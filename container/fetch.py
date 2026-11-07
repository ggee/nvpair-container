"""Download and verify the official Linux x64 service bundle before extraction."""

import hashlib
import io
from pathlib import Path
import re
import sys
import urllib.request
import zipfile


def extract(data, expected, destination):
    if not re.fullmatch(r"[0-9a-f]{64}", expected):
        raise ValueError("expected SHA-256 must contain 64 lowercase hexadecimal digits")
    if hashlib.sha256(data).hexdigest() != expected:
        raise ValueError("PAIR archive checksum mismatch")
    root = Path(destination).resolve()
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        for entry in archive.infolist():
            target = (root / entry.filename).resolve()
            if not target.is_relative_to(root) or (entry.external_attr >> 16) & 0o170000 == 0o120000:
                raise ValueError("unsafe archive entry")
        archive.extractall(root)
    if not (root / "nvpair-ui-broker").is_file():
        raise ValueError("archive missing nvpair-ui-broker")


if __name__ == "__main__":
    version, checksum, destination = sys.argv[1:]
    if not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", version):
        raise ValueError("expected numeric release version")
    url = ("https://github.com/NVIDIA/Personal-AI-Router/releases/download/"
           f"v{version}/service-binaries-linux-x64.zip")
    with urllib.request.urlopen(url, timeout=120) as response:
        extract(response.read(), checksum, destination)
