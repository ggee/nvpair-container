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

## Separate engine and model storage — 2026-11-14

- Built `nvpair-storage-test:local` with Docker Desktop 4.79.0 / Engine 29.5.3
  through the Windows CLI. The build downloaded and checksum-verified the pinned
  upstream v1.0.0 archive.
- Ran two network-isolated disposable containers with the read-only rootfs,
  startup capabilities, and no-new-privileges configuration used by the template.
  Separate disposable volumes were mounted at `/state`, the profile's
  `engine-bin` directory, and `/state/.llamacpp`.
- The real entrypoint initialized Docker-created parent directories and the
  storage mounts. Probes confirmed UID/GID 10002, no supplementary groups, zero
  effective capabilities, mode 0700 directories, and writable settings, engine,
  and model locations. Marker contents survived container recreation.
- Inspected each volume independently to verify engine/model markers were in
  their dedicated volumes and absent from the underlying state volume. All
  disposable volumes were removed after testing.

These checks used Python probes and marker files, not installed inference engines
or downloaded models. They establish Docker storage separation and persistence
with nested volumes; Unraid host bind mounts, llama.cpp installation/inference,
GPU access, and full PAIR startup/pairing remain unvalidated. The test image is
local only; no image was published and no host service was deployed.

## Wrapper revision tag — 2026-11-14

- Built the local image `greggee/nvpair-container:1.0.0-2`, with matching OCI
  image-version label. PAIR version 1.0.0 and its archive SHA-256 are unchanged.
- Compose and the Unraid template now reference this revision. Future
  container releases increment the suffix independently of the PAIR version;
  development changes and test rebuilds retain the current tag.
- No image was pushed to a registry.

## Single external share — 2026-11-14

- Initially tested this layout under a temporary `1.0.0-3` tag, then rebuilt it
  as `greggee/nvpair-container:1.0.0-2` to retain the current release revision.
  PAIR version and checksum remain unchanged. Development rebuilds keep the
  current tag until a new container version is released.
- All 21 Python tests passed. Base, NVIDIA, routing-only, external-storage,
  and combined NVIDIA/external-storage Compose configurations validated, along
  with the Unraid XML. The template now contains only `/state` and `/storage`
  path mappings.
- Real network-isolated Docker containers used disposable state and storage
  volumes. Startup created private `engines`, `models`, and `models/llamacpp`
  subdirectories and replaced empty legacy directories with the expected
  symlinks. The storage volume root's original ownership and mode were preserved.
- Verified writable linked paths as UID/GID 10002 with no unrelated groups and
  zero effective capabilities, persistence across container recreation, and
  direct non-root startup on initialized storage. Independent volume inspection
  confirmed settings/links in state and engine/model marker files in storage.
- Confirmed startup refuses a nonempty existing model directory and leaves its
  file contents intact. Unit coverage also checks conflicting mounts, unexpected
  symlinks, symlinked storage directories, and a missing storage mount.
- All disposable test volumes were removed. The image was not published and no
  host services were deployed. Tests used Python probes and marker files;
  Unraid bind mounts, llama.cpp installation/inference, GPU access, and full PAIR
  startup/pairing remain unvalidated.
