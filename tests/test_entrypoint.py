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

    def test_engine_mounts_prepare_docker_created_parents_without_changing_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "state"
            engines = root / "config/Nvidia Corporation/Personal AI Router/engine-bin"
            models = root / ".llamacpp"
            engines.mkdir(parents=True)
            models.mkdir()
            model = models / "existing.gguf"
            model.write_bytes(b"existing model")
            before = model.stat()
            mounts = Path(directory) / "mountinfo"
            mounts.write_text("".join(
                "1 0 0:1 / " + str(path).replace(" ", r"\040") + " rw - ext4 /dev/test rw\n"
                for path in (engines, models)
            ))
            entrypoint.prepare_engine_storage(root, os.getuid(), os.getgid(), mounts)
            for path in (engines, models, engines.parent, root / "config"):
                self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o700)
            self.assertEqual(model.read_bytes(), b"existing model")
            self.assertEqual(model.stat().st_mode, before.st_mode)
            self.assertEqual(model.stat().st_mtime_ns, before.st_mtime_ns)

    def test_no_external_mounts_leave_existing_profile_alone(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "state"
            root.mkdir()
            mounts = Path(directory) / "mountinfo"
            mounts.write_text("")
            entrypoint.prepare_engine_storage(root, os.getuid(), os.getgid(), mounts)
            self.assertEqual(list(root.iterdir()), [])

    def storage_layout(self, directory):
        base = Path(directory)
        state, storage = base / "state", base / "storage"
        state.mkdir()
        storage.mkdir(mode=0o755)
        mounts = base / "mountinfo"
        mounts.write_text(f"1 0 0:1 / {storage} rw - ext4 /dev/test rw\n")
        return state, storage, mounts

    def test_share_creates_private_subdirectories_and_persistent_links(self):
        with tempfile.TemporaryDirectory() as directory:
            state, storage, mounts = self.storage_layout(directory)
            root_mode = storage.stat().st_mode
            for attempt in range(2):
                entrypoint.prepare_engine_storage(state, os.getuid(), os.getgid(), mounts, storage)
                for relative in ("engines", "models", "models/llamacpp"):
                    self.assertEqual(stat.S_IMODE((storage / relative).stat().st_mode), 0o700)
                link = state / ".llamacpp"
                self.assertTrue(link.is_symlink())
                self.assertEqual(link.resolve(), storage / "models/llamacpp")
                engine_link = state / "config/Nvidia Corporation/Personal AI Router/engine-bin"
                self.assertEqual(engine_link.resolve(), storage / "engines")
                if attempt == 0:
                    (link / "test.gguf").write_bytes(b"model")
                    (engine_link / "test-engine").write_bytes(b"engine")
                self.assertEqual((link / "test.gguf").read_bytes(), b"model")
                self.assertEqual((engine_link / "test-engine").read_bytes(), b"engine")
            self.assertEqual(storage.stat().st_mode, root_mode)

    def test_share_refuses_existing_data_or_unexpected_link(self):
        for kind in ("data", "link"):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as directory:
                state, storage, mounts = self.storage_layout(directory)
                original = state / ".llamacpp"
                if kind == "data":
                    original.mkdir()
                    (original / "existing.gguf").write_bytes(b"keep")
                else:
                    original.symlink_to(Path(directory) / "elsewhere")
                with self.assertRaisesRegex(RuntimeError, "migrate"):
                    entrypoint.prepare_engine_storage(state, os.getuid(), os.getgid(), mounts, storage)
                if kind == "data":
                    self.assertEqual((original / "existing.gguf").read_bytes(), b"keep")
                else:
                    self.assertEqual(os.readlink(original), str(Path(directory) / "elsewhere"))

    def test_share_rejects_symlinked_storage_subdirectory(self):
        with tempfile.TemporaryDirectory() as directory:
            state, storage, mounts = self.storage_layout(directory)
            elsewhere = Path(directory) / "elsewhere"
            elsewhere.mkdir(mode=0o755)
            (storage / "engines").symlink_to(elsewhere)
            before = elsewhere.stat().st_mode
            with self.assertRaises(OSError):
                entrypoint.prepare_engine_storage(state, os.getuid(), os.getgid(), mounts, storage)
            self.assertEqual(elsewhere.stat().st_mode, before)

    def test_share_mount_cannot_be_removed_while_links_remain(self):
        with tempfile.TemporaryDirectory() as directory:
            state, storage, mounts = self.storage_layout(directory)
            entrypoint.prepare_engine_storage(state, os.getuid(), os.getgid(), mounts, storage)
            mounts.write_text("")
            with self.assertRaisesRegex(RuntimeError, "restore the /storage mount"):
                entrypoint.prepare_engine_storage(state, os.getuid(), os.getgid(), mounts, storage)

    def test_share_and_legacy_mounts_cannot_be_combined(self):
        with tempfile.TemporaryDirectory() as directory:
            state, storage, mounts = self.storage_layout(directory)
            with mounts.open("a") as stream:
                stream.write(f"2 0 0:2 / {state}/.llamacpp rw - ext4 /dev/test rw\n")
            with self.assertRaisesRegex(RuntimeError, "remove the old"):
                entrypoint.prepare_engine_storage(state, os.getuid(), os.getgid(), mounts, storage)
