# Initial validation — 2026-11-06

Completed in WSL:

- All 11 Python tests passed, including an actual private Unix-socket RPC
  round trip, unhealthy-backend/proxy rejection, router-mode health behavior,
  preservation of existing settings, archive checksum/path validation, and XML
  template defaults.
- The cached official v1.0.0 services archive matched the pinned SHA-256 and
  extracted successfully using the project's extraction code (14 files).
- Docker Compose v2.39.4 `config --quiet` passed for the base configuration,
  NVIDIA override, and routing-only override. The temporary Compose executable
  was verified against the official release checksum.

Pending:

- Build the Docker image and validate runtime startup, health, pairing,
  shutdown/restart, and persistent identity using isolated state.
- Install the template on Unraid and validate its generated container settings.
- Confirm GTX 1080 driver/runtime visibility, non-root `nvidia-smi`, and live
  telemetry in Windows PAIR.
- Validate routing-only inference through a paired peer and inspect its actual
  proxy port.

Docker is unavailable in the current WSL distro. The original Ubuntu deployment
is evidence for the starting wrapper, not runtime validation of this derivative.
No production services were changed and no model requests were submitted.

## Automatic state initialization — 2026-11-06

- All 14 Python tests passed, including private-directory creation, existing
  identity preservation, and rejection of symlink/file state paths.
- Base, NVIDIA, and routing-only Compose configurations validated; Unraid XML
  parsed successfully.
- Built the updated Linux/amd64 image using Docker Desktop from WSL. Upstream
  PAIR remains at the same pinned version and SHA-256; the image tag stays `1.0.0`.
- Actual network-isolated Docker containers with disposable volume state verified
  initialization of a root-owned directory, repeated startup with existing private
  state, writable PAIR profile initialization, and direct non-root startup with
  pre-provisioned state. The process ran as UID/GID 10002, with no unrelated groups,
  zero effective/permitted capabilities, and no ability to regain UID 0. Directory
  mode was 0700 and a new private test identity was 0600 and survived restart.
- Missing initialization capabilities caused startup to fail before executing
  the application command. All disposable test volumes were removed.

These entrypoint checks executed Python probes, not PAIR workers. Full PAIR
startup, pairing, inference, GPU telemetry, and Unraid host validation remain
pending. No image was pushed and no host deployment was performed.
