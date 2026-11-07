"""Local PAIR administration. Pairing PINs are prompted, never command arguments."""

import argparse
import getpass
import json
import sys

from supervisor import checked_rpc


def pending():
    invitations = {}
    events = checked_rpc("control:events")
    for event in events:
        if event.get("method") == "cluster:invite-received":
            invite = event.get("params", {})
            invitations[invite.get("inviteId", invite.get("id"))] = invite
    active = []
    for ident, invite in invitations.items():
        if ident:
            status = checked_rpc("cluster:invite-status", {"inviteId": ident})
            if status.get("state") == "pending":
                active.append({"inviteId": ident, "from": invite.get("from", invite.get("fromNodeId", "peer"))})
    return active


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["status", "pending", "accept", "reject"])
    args = parser.parse_args()
    if args.command == "status":
        identity = checked_rpc("cluster:get-node-id")
        members = checked_rpc("nodes:get-initial")["nodes"]
        print(json.dumps({"name": identity["name"], "paired": bool(identity.get("clusterId")),
                          "members": [{"name": m["name"], "state": m["state"]} for m in members],
                          "engine": checked_rpc("engine:status", {"engine": "ollama"}),
                          "proxy": checked_rpc("ollama-proxy:get-status")}, indent=2))
        return
    invites = pending()
    if args.command == "pending":
        print(json.dumps(invites, indent=2))
        return
    if len(invites) != 1:
        raise RuntimeError("Expected one pending invitation. Send a fresh invitation from Windows PAIR, then retry.")
    params = {"inviteId": invites[0]["inviteId"], "accept": args.command == "accept"}
    if params["accept"]:
        if not sys.stdin.isatty():
            raise RuntimeError("Accept requires an interactive terminal; rerun docker exec -it nvpair python3 /app/admin.py accept.")
        pin = getpass.getpass("PIN displayed by the inviting PAIR node: ").strip()
        if len(pin) != 6 or not pin.isascii() or not pin.isdecimal():
            raise ValueError("PAIR PIN must contain exactly six digits")
        params["pin"] = pin
    result = checked_rpc("cluster:respond-to-invite", params)
    print("Pairing result:", result["state"])
    if result["state"] not in ("paired", "declined"):
        raise RuntimeError("Pairing did not complete; send a fresh invitation and retry")


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, ValueError, OSError) as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
