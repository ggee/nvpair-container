"""Prepare private state, then permanently drop root before executing PAIR."""

import os
import stat
import sys


UID = GID = 10002


def prepare_state(path="/state", uid=UID, gid=GID):
    os.umask(0o077)
    try:
        os.mkdir(path, 0o700)
    except FileExistsError:
        pass
    # Never follow a symlink or recursively change existing identity files.
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        current = os.fstat(fd)
        if (current.st_uid, current.st_gid) != (uid, gid):
            os.fchown(fd, uid, gid)
        if stat.S_IMODE(current.st_mode) != 0o700:
            os.fchmod(fd, 0o700)
    finally:
        os.close(fd)


def main():
    prepare_state()
    if os.geteuid() == 0:
        os.setgroups([])
        os.setgid(GID)
        os.setuid(UID)
    if os.getresuid() != (UID, UID, UID) or os.getresgid() != (GID, GID, GID):
        raise RuntimeError("PAIR must run as UID/GID 10002:10002")
    command = sys.argv[1:] or ["python3", "/app/supervisor.py"]
    os.execvp(command[0], command)


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError) as error:
        print(f"PAIR startup failed: {error}", file=sys.stderr)
        sys.exit(1)
