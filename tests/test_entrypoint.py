import os
from pathlib import Path
import stat
import tempfile
import unittest

from test_container import load


entrypoint = load("entrypoint")


class StateInitializationTests(unittest.TestCase):
    def setUp(self):
        self.old_umask = os.umask(0o022)
        self.addCleanup(os.umask, self.old_umask)

    def test_fresh_directory_is_private_and_writable(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "state"
            entrypoint.prepare_state(path, os.getuid(), os.getgid())
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o700)
            (path / "identity").write_bytes(b"private test identity")
            self.assertEqual(stat.S_IMODE((path / "identity").stat().st_mode), 0o600)

    def test_existing_identity_is_untouched_on_repeated_start(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            path.chmod(0o755)
            identity = path / "identity"
            identity.write_bytes(b"existing test identity")
            before = identity.stat()
            for _ in range(2):
                entrypoint.prepare_state(path, os.getuid(), os.getgid())
            self.assertEqual(identity.read_bytes(), b"existing test identity")
            self.assertEqual(identity.stat().st_mtime_ns, before.st_mtime_ns)
            self.assertEqual(identity.stat().st_mode, before.st_mode)
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o700)

    def test_symlink_and_regular_file_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "target"
            target.mkdir(mode=0o755)
            link = root / "link"
            link.symlink_to(target, target_is_directory=True)
            file = root / "file"
            file.write_bytes(b"untouched")
            for path in (link, file):
                with self.subTest(path=path), self.assertRaises(OSError):
                    entrypoint.prepare_state(path, os.getuid(), os.getgid())
            self.assertEqual(stat.S_IMODE(target.stat().st_mode), 0o755)
            self.assertEqual(file.read_bytes(), b"untouched")
