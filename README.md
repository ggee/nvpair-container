# nvpair-container

An independent, unofficial headless container for
[NVIDIA Personal AI Router](https://github.com/NVIDIA/Personal-AI-Router).
It packages the checksum-verified **v1.0.0 Linux x64 service bundle**, a Python
supervisor, health checks, and a local pairing helper. Linux/amd64 only.

Ollama, models, GPU drivers, and a desktop UI are separate. Manage the cluster
from an existing PAIR desktop client. This project does not contain the WSL
manual-peer compatibility patch. Images are published as
`greggee/nvpair-container` on Docker Hub.

## Build and run with existing Ollama

Ollama must already be healthy on host loopback `127.0.0.1:11434`. For a separate
Ollama container, publish its backend to that loopback address. PAIR uses host
networking and adopts the backend; its proxy is expected on 11435. Avoid running
another PAIR instance on the same host.

Before starting, restrict the following host-network listeners to loopback and
your trusted LAN: **TCP 11435, 14318–14323 and UDP 5353**. Block untrusted IPv4
and IPv6 sources. There are no firewall rules inside this image. Host networking
does not use Docker port mappings. Check for port conflicts before deployment.
Do not expose these listeners to the Internet.

```bash
cp .env.example .env
# Edit PAIR_NODE_NAME and PAIR_STATE_DIR for this host.
docker compose build
docker compose up -d
docker compose ps
docker exec --user=10002:10002 nvpair python3 /app/admin.py status
```

The node name shown in PAIR comes from the container hostname. For Compose, set
`PAIR_NODE_NAME=Tower-AI` in `.env`, then run `docker compose up -d` to recreate
the container with that hostname. Use a unique hostname with letters, numbers,
and hyphens. Keep the same state path to preserve identity and pairing. For
Unraid, edit `--hostname=PAIR-UNRAID` in **Advanced View → Extra Parameters** and
click **Apply**; changing the container's **Name** alone does not rename the node.

Docker creates a missing state directory automatically. The entrypoint starts as
root, sets only the state directory itself to owner `10002:10002` and mode `0700`,
then permanently switches to that UID/GID before starting PAIR. It clears
supplementary groups and uses a private umask. Existing identity files are not
rewritten or recursively re-owned. Bind-mount a dedicated local appdata directory;
filesystems that reject ownership changes need a pre-provisioned directory.
Compose and the Unraid template grant only the five capabilities needed for this
initialization, with read-only rootfs and no-new-privileges retained. Do not set
`--user=10002:10002` for automatic initialization. For a manually prepared state
directory, running directly as that UID/GID with all capabilities dropped remains
supported.
Settings are initialized with `force_ports: false` only for a fresh profile;
existing settings and pairing are preserved. Port environment variables only
validate expected ports; they do not reconfigure the upstream services.

In Windows PAIR, choose **Add node** and select this node (or enter its LAN IP).
Then accept the invitation inside the running container:

```bash
docker exec --user=10002:10002 nvpair python3 /app/admin.py pending
docker exec --user=10002:10002 -it nvpair python3 /app/admin.py accept
```

Enter the displayed six-digit PIN at the hidden prompt. The helper also supports
`reject`. Invitations expire; send a fresh one if necessary. Pairing state lives
under `/state/config/Nvidia Corporation/Personal AI Router`. Use fresh state for
each additional node. Never clone a running node's identity to another host.

The supervisor closes broker stdin on SIGTERM so workers drain. Three consecutive
health failures after a startup grace period make the supervisor exit; Docker's
`unless-stopped` policy restarts it. `docker compose down` intentionally stops
the service without deleting state. Back up state privately; it contains keys.

## Optional NVIDIA telemetry

PAIR's Linux collector uses `nvidia-smi` for NVIDIA GPU name, utilization, and
VRAM statistics. Install a host driver compatible with your GPU and the NVIDIA
Container Toolkit/runtime. On Unraid, see the
[Nvidia-Driver plugin](https://ca.unraid.net/apps/nvidia-driver-1aax6kn0zkg6t7).
Record the GPU UUID from `nvidia-smi --query-gpu=uuid --format=csv,noheader` in
`.env` as `NVIDIA_VISIBLE_DEVICES=GPU-...`, then run:

```bash
docker compose -f compose.yml -f examples/nvidia.yml up -d
docker exec nvpair nvidia-smi \
  --query-gpu=name,utilization.gpu,memory.used,memory.total --format=csv
```

Use the same Compose files for subsequent down/up operations. NVIDIA's `utility`
capability supplies `nvidia-smi` and NVML; a CUDA base image is unnecessary for
telemetry. See [NVIDIA's runtime documentation](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/docker-specialized.html).
Ollama separately needs compute access. Both containers can observe/use the same
GPU; PAIR reports device-wide activity. This does not establish GPU-aware routing.
GTX 1080 telemetry requires a compatible host driver; CUDA compatibility for
Ollama is a separate check. Linux AMD utilization remains unsupported upstream.

Restart PAIR after fixing NVIDIA runtime visibility: upstream can latch a failed
`nvidia-smi` probe until restart. Container CPU/RAM figures may reflect container
limits and are not guaranteed to describe the entire host.

## Unraid

See [the Unraid guide](unraid/README.md) and [local template](unraid/nvpair.xml).
This is a custom image, not a Community Applications listing or NVIDIA release.

### Engine and model storage

The Unraid template maps `/mnt/user/nvpair` to `/storage`. Startup creates
`engines/` and `models/llamacpp/` inside that share, assigning only those
subdirectories (including `models/`) to UID/GID `10002:10002` with mode `0700`.
The share root's ownership and permissions are preserved. Existing contents are
not recursively re-owned. Use dedicated storage for one node.

Settings and pairing remain in appdata through `/state`. Startup creates these
internal symlinks so upstream can keep its expected paths:

| PAIR path in the container | Target | Unraid host location |
| --- | --- | --- |
| `/state/config/Nvidia Corporation/Personal AI Router/engine-bin` | `/storage/engines` | `/mnt/user/nvpair/engines` |
| `/state/.llamacpp` | `/storage/models/llamacpp` | `/mnt/user/nvpair/models/llamacpp` |

For Compose, set `PAIR_STORAGE_DIR` in `.env` to a dedicated absolute path outside
appdata, then use:

```bash
docker compose -f compose.yml -f examples/engine-storage.yml up -d --build
```

Use the same override for subsequent Compose operations. This configures storage
only: the wrapper still enables only the Ollama proxy and requires a separately
installed Ollama by default. Its model storage is configured separately. Local
llama.cpp inference is not enabled or validated by this mapping.

For existing installations, stop the container and back up state before changing
mappings. If upgrading from the two-mount layout, remove the old `engine-bin` and
`.llamacpp` mount entries and add `/mnt/user/nvpair:/storage`; existing external
files already in `engines/` and `models/llamacpp/` can remain there. Startup
replaces empty directories at the old container paths with symlinks. If those
paths contain data in appdata or point elsewhere, startup refuses to continue:
copy the contents to the appropriate external subdirectories preserving ownership,
then move the old directories out of the way. Keep backups until verified. No
automatic data migration is performed. Restore the `/storage` mapping if startup
reports that a link requires it. Legacy nested mounts remain supported when
`/storage` is absent, but must not be combined with the new layout.

Importing a template does not update an existing container's settings. This layout
has automated and Docker checks but has not been validated on Unraid.

## Experimental routing-only mode

Without local Ollama, the original wrapper would restart repeatedly. This
override removes that backend health requirement while retaining broker/proxy
checks and permits whichever proxy port upstream selects:

```bash
docker compose -f compose.yml -f examples/router-only.yml up -d
docker exec --user=10002:10002 nvpair python3 /app/admin.py status
```

Inspect the actual proxy port, adjust LAN restrictions accordingly, pair, and
test a model hosted on a peer. This mode has unit coverage but has **not** had
an end-to-end container test. It does not solve upstream WSL/NAT discovery gaps.

## Development and verification

```bash
python3 -m unittest discover -s tests -v
docker compose config --quiet
NVIDIA_VISIBLE_DEVICES=GPU-EXAMPLE docker compose -f compose.yml -f examples/nvidia.yml config --quiet
docker compose -f compose.yml -f examples/router-only.yml config --quiet
```

Builds use a digest-pinned Python base and verify the official archive SHA-256
before extraction. Image tags use `<PAIR version>-<wrapper revision>`, currently
`greggee/nvpair-container:1.0.0-2`: upstream PAIR 1.0.0, wrapper revision 2.
Increment the revision suffix only when releasing a new container version, not
for development changes or test rebuilds. At release time, update the Compose
image, Unraid template, Dockerfile image-version label, and documentation. For
wrapper-only releases, keep `PAIR_VERSION` and `PAIR_SHA256` unchanged. For an upstream upgrade, review
upstream, update both pins and the notices, and reset the wrapper revision to 1
for the new PAIR version. Build and validate using isolated state. Do not replace
individual workers. Building or updating these references does not publish an
image to Docker Hub.

The original adopted-Ollama wrapper was validated on an Ubuntu AMD host. This
portable derivative has automated tests; Unraid deployment, NVIDIA telemetry,
and router-only inference still require host validation. No production service
is modified by creating or testing this repository.

The wrapper comes from the ai-server-build project and is licensed under the
[Apache License 2.0](LICENSE). NVIDIA software and third-party components retain
their respective licenses; upstream licensing and notices are preserved under
`third-party/`.
