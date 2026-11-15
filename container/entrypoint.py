"""Prepare private state, then permanently drop root before executing PAIR."""

import os
from pathlib import Path
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
    prepare_engine_storage()
    if os.geteuid() == 0:
        os.setgroups([])
        os.setgid(GID)
        os.setuid(UID)
    if os.getresuid() != (UID, UID, UID) or os.getresgid() != (GID, GID, GID):
        raise RuntimeError("PAIR must run as UID/GID 10002:10002")
    command = sys.argv[1:] or ["python3", "/app/supervisor.py"]
    os.execvp(command[0], command)


def prepare_engine_storage(state="/state", uid=UID, gid=GID, mountinfo="/proc/self/mountinfo"):
    """Initialize dedicated bind mounts, including parents Docker may create."""
    root = Path(state)
    profile = root / "config/Nvidia Corporation/Personal AI Router"
    engines = profile / "engine-bin"
    models = root / ".llamacpp"
    # ismount() cannot reliably detect bind mounts on the same filesystem.
    mounts = set()
    for line in Path(mountinfo).read_text().splitlines():
        target = line.split()[4]
        for escaped, literal in ((r"\040", " "), (r"\011", "\t"), (r"\012", "\n"), (r"\134", "\\")):
            target = target.replace(escaped, literal)
        mounts.add(target)
    if str(engines) in mounts:
        # Work from the state root down; never follow symlinks in parents.
        for directory in (root / "config", root / "config/Nvidia Corporation", profile, engines):
            prepare_state(directory, uid, gid)
    if str(models) in mounts:
        prepare_state(models, uid, gid)


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError) as error:
        print(f"PAIR startup failed: {error}", file=sys.stderr)
        sys.exit(1)
