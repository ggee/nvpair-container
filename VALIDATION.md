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
