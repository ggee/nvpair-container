# nvpair-container

This is an independent headless container wrapper for NVIDIA Personal AI Router.
Keep upstream versions and download checksums pinned together. Preserve upstream
license and third-party notices. Do not commit state, certificates, keys, or PINs.

Run `python3 -m unittest discover -s tests -v` and validate Compose and Unraid XML
after changes. Use isolated state for runtime tests. Do not start a second PAIR
worker tree on ports already used by another node. Host networking exposes
listeners: document the ports and preserve trusted-LAN restrictions.

Do not deploy to a host, publish an image/repository, or create a commit unless
the user asks. Do not claim Unraid or GPU validation based on mocked tests.
