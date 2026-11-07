import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import socket
import tempfile
import threading
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET
import zipfile


ROOT = Path(__file__).resolve().parents[1]


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "container" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


supervisor = load("supervisor")
fetch = load("fetch")


class HealthTests(unittest.TestCase):
    def setUp(self):
        self.environment = patch.dict(os.environ, {
            "PAIR_REQUIRE_OLLAMA": "true", "PAIR_OLLAMA_PORT": "11434",
            "PAIR_EXPECT_PROXY_PORT": "11435",
        })
        self.environment.start()
        self.addCleanup(self.environment.stop)

    @staticmethod
    def replies(method, params=None, timeout=None):
        return {
            "ping": {"pong": True},
            "engine:status": {"healthy": True, "running": True, "port": 11434},
            "ollama-proxy:get-status": {"ready": True, "port": 11435},
        }[method]

    def test_adopted_backend(self):
        with patch.object(supervisor, "checked_rpc", side_effect=self.replies):
            supervisor.health()

    def test_backend_unhealthy_is_failure(self):
        def reply(method, *args, **kwargs):
            return {"healthy": False} if method == "engine:status" else self.replies(method)
        with patch.object(supervisor, "checked_rpc", side_effect=reply):
            with self.assertRaisesRegex(RuntimeError, "Ollama"):
                supervisor.health()

    def test_router_skips_engine_but_requires_proxy(self):
        with patch.dict(os.environ, {"PAIR_REQUIRE_OLLAMA": "false", "PAIR_EXPECT_PROXY_PORT": "0"}):
            with patch.object(supervisor, "checked_rpc", side_effect=[{"pong": True}, {"ready": True, "port": 11434}]) as rpc:
                supervisor.health()
                self.assertEqual([c.args[0] for c in rpc.call_args_list], ["ping", "ollama-proxy:get-status"])
            with patch.object(supervisor, "checked_rpc", side_effect=[{"pong": True}, {"ready": False}]):
                with self.assertRaises(RuntimeError):
                    supervisor.health()

    def test_wrong_proxy_port_fails(self):
        with patch.dict(os.environ, {"PAIR_EXPECT_PROXY_PORT": "23456"}):
            with patch.object(supervisor, "checked_rpc", side_effect=self.replies):
                with self.assertRaises(RuntimeError):
                    supervisor.health()

    def test_initialize_preserves_settings(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.dict(os.environ, {"XDG_CONFIG_HOME": directory}):
                supervisor.initialize()
                settings = Path(directory) / "Nvidia Corporation/Personal AI Router/settings.json"
                self.assertEqual(json.loads(settings.read_text()), {"force_ports": False})
                settings.write_text('{"force_ports":true,"existing":"preserved"}')
                supervisor.initialize()
                self.assertEqual(json.loads(settings.read_text())["existing"], "preserved")

    def test_invalid_configuration(self):
        for key, value in (("PAIR_REQUIRE_OLLAMA", "typo"), ("PAIR_OLLAMA_PORT", "0"), ("PAIR_EXPECT_PROXY_PORT", "65536")):
            with self.subTest(key=key), patch.dict(os.environ, {key: value}):
                with self.assertRaises(ValueError):
                    supervisor.initialize()


class ArchiveTests(unittest.TestCase):
    def archive(self, name):
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, "w") as archive:
            archive.writestr(name, b"test")
        return stream.getvalue()

    def test_verified_extract(self):
        data = self.archive("nvpair-ui-broker")
        with tempfile.TemporaryDirectory() as directory:
            fetch.extract(data, hashlib.sha256(data).hexdigest(), directory)
            self.assertEqual((Path(directory) / "nvpair-ui-broker").read_bytes(), b"test")

    def test_checksum_rejected_before_extract(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "checksum"):
                fetch.extract(self.archive("nvpair-ui-broker"), "0" * 64, directory)
            self.assertEqual(list(Path(directory).iterdir()), [])

    def test_traversal_rejected(self):
        data = self.archive("../outside")
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "unsafe"):
                fetch.extract(data, hashlib.sha256(data).hexdigest(), directory)


class AdministrationTests(unittest.TestCase):
    def test_unix_rpc_round_trip_and_error(self):
        with tempfile.TemporaryDirectory() as directory:
            address = str(Path(directory) / "control.sock")
            with socket.socket(socket.AF_UNIX) as server:
                server.bind(address)
                server.listen()
                def worker():
                    for response in ({"result": {"pong": True}}, {"error": "denied"}):
                        connection, _ = server.accept()
                        with connection:
                            request = json.loads(connection.makefile("rb").readline())
                            self.assertEqual(request["method"], "ping")
                            connection.sendall(json.dumps(response).encode() + b"\n")
                thread = threading.Thread(target=worker, daemon=True)
                thread.start()
                with patch.object(supervisor, "SOCKET", address):
                    self.assertEqual(supervisor.checked_rpc("ping", timeout=2), {"pong": True})
                    with self.assertRaisesRegex(RuntimeError, "denied"):
                        supervisor.checked_rpc("ping", timeout=2)
                thread.join(timeout=3)
                self.assertFalse(thread.is_alive())

    def test_unraid_template_preserves_nonprivileged_defaults(self):
        root = ET.parse(ROOT / "unraid/nvpair.xml").getroot()
        self.assertEqual(root.findtext("Network"), "host")
        self.assertEqual(root.findtext("Privileged"), "false")
        self.assertNotIn("--user=", root.findtext("ExtraParams"))
        for capability in ("CHOWN", "FOWNER", "DAC_OVERRIDE", "SETUID", "SETGID"):
            self.assertIn(f"--cap-add={capability}", root.findtext("ExtraParams"))
        self.assertIn("--read-only", root.findtext("ExtraParams"))
        configs = {c.attrib["Target"]: c.text for c in root.findall("Config")}
        self.assertEqual(configs["NVIDIA_DRIVER_CAPABILITIES"], "utility")
        self.assertEqual(configs["NVIDIA_VISIBLE_DEVICES"], "void")


if __name__ == "__main__":
    unittest.main()
