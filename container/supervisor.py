"""Supervise PAIR's broker through a private, container-local Unix socket.

No TCP administration endpoint; no shell execution or Docker socket access.
The broker owns worker shutdown. State and the private socket live in /state.
"""

import collections
import itertools
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import threading

SOCKET = "/state/control.sock"


def rpc(method, params=None, timeout=100):
    with socket.socket(socket.AF_UNIX) as conn:
        conn.settimeout(timeout)
        conn.connect(SOCKET)
        conn.sendall(json.dumps({"method": method, "params": params or {}}).encode() + b"\n")
        return json.loads(conn.makefile("rb").readline())


def checked_rpc(method, params=None, timeout=100):
    response = rpc(method, params, timeout)
    if "error" in response:
        raise RuntimeError(response["error"])
    return response["result"]


def require_ollama():
    value = os.environ.get("PAIR_REQUIRE_OLLAMA", "true").lower()
    if value not in ("true", "false"):
        raise ValueError("PAIR_REQUIRE_OLLAMA must be true or false")
    return value == "true"


def health():
    if not checked_rpc("ping", timeout=5).get("pong"):
        raise RuntimeError("broker ping failed")
    if require_ollama():
        status = checked_rpc("engine:status", {"engine": "ollama"}, timeout=5)
        port = int(os.environ.get("PAIR_OLLAMA_PORT", "11434"))
        if not (status.get("healthy") and status.get("running") and status.get("port") == port):
            raise RuntimeError(f"local Ollama not healthy on port {port}")
    proxy = checked_rpc("ollama-proxy:get-status", timeout=5)
    port = int(os.environ.get("PAIR_EXPECT_PROXY_PORT", "11435"))
    if not proxy.get("ready") or (port and proxy.get("port") != port):
        raise RuntimeError(f"PAIR proxy not ready on expected port {port or 'auto'}")


def initialize():
    # Fail early on invalid settings, without launching the upstream workers.
    require_ollama()
    for key, default in (("PAIR_OLLAMA_PORT", "11434"), ("PAIR_EXPECT_PROXY_PORT", "11435")):
        port = int(os.environ.get(key, default))
        if not (0 <= port <= 65535) or (key == "PAIR_OLLAMA_PORT" and port == 0):
            raise ValueError(f"invalid {key}")
    profile = Path(os.environ.get("XDG_CONFIG_HOME", "/state/config")) / "Nvidia Corporation/Personal AI Router"
    profile.mkdir(parents=True, exist_ok=True, mode=0o700)
    settings = profile / "settings.json"
    try:
        # Existing identity and settings always win; never overwrite paired state.
        with settings.open("x") as stream:
            json.dump({"force_ports": False}, stream)
    except FileExistsError:
        pass


def serve():
    os.umask(0o077)
    initialize()
    broker = subprocess.Popen(
        ["./nvpair-ui-broker", "--proxy-engines", "ollama"],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, bufsize=1,
    )
    pending, events = {}, collections.deque(maxlen=500)
    lock = threading.Lock()
    ids = itertools.count(1)

    def reader():
        for line in broker.stdout:
            try:
                frame = json.loads(line)
            except ValueError:
                continue
            with lock:
                waiter = pending.get(frame.get("id"))
                if waiter:
                    waiter[1].append(frame)
                    waiter[0].set()
                elif "method" in frame:
                    events.append(frame)
        with lock:
            for ready, result in pending.values():
                result.append({"error": "broker exited"})
                ready.set()

    threading.Thread(target=reader, daemon=True).start()

    def handle(conn):
        with conn:
            request = json.loads(conn.makefile("rb").readline())
            if request["method"] == "control:events":
                with lock:
                    response = {"result": list(events)}
            else:
                ident = next(ids)
                ready, result = threading.Event(), []
                with lock:
                    pending[ident] = ready, result
                    broker.stdin.write(json.dumps({"jsonrpc": "2.0", "id": ident, **request}) + "\n")
                    broker.stdin.flush()
                ready.wait(110)
                with lock:
                    pending.pop(ident, None)
                response = result[0] if result else {"error": "RPC timed out"}
            conn.sendall(json.dumps(response).encode() + b"\n")

    listener = socket.socket(socket.AF_UNIX)
    if os.path.exists(SOCKET):
        os.unlink(SOCKET)
    listener.bind(SOCKET)
    listener.listen()
    listener.settimeout(1)
    stopped, unhealthy = threading.Event(), threading.Event()

    def watchdog():
        # Allow discovery and adopted-backend startup to settle before checking.
        if stopped.wait(90):
            return
        failures = 0
        while not stopped.is_set():
            try:
                health()
                failures = 0
            except (AssertionError, OSError, ValueError, RuntimeError):
                failures += 1
            if failures >= 3:
                print("PAIR health failed three consecutive checks; restarting", file=sys.stderr)
                unhealthy.set()
                stopped.set()
                return
            stopped.wait(30)

    threading.Thread(target=watchdog, daemon=True).start()
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, lambda *_: stopped.set())
    try:
        while not stopped.is_set() and broker.poll() is None:
            try:
                conn, _ = listener.accept()
            except socket.timeout:
                continue
            threading.Thread(target=handle, args=(conn,), daemon=True).start()
    finally:
        unexpected = not stopped.is_set()
        listener.close()
        if broker.poll() is None:
            broker.stdin.close()
        broker.wait()
        stopped.set()
        if os.path.exists(SOCKET):
            os.unlink(SOCKET)
    # A broker exit, even with code 0, must not silently leave a dead node.
    return 1 if unhealthy.is_set() or unexpected else broker.returncode


if __name__ == "__main__":
    if sys.argv[1:] == ["--health"]:
        try:
            health()
        except (AssertionError, OSError, ValueError, RuntimeError) as error:
            print(f"PAIR not ready: {error}", file=sys.stderr)
            sys.exit(1)
        print("PAIR ready")
    else:
        sys.exit(serve())
