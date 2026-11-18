# Unraid deployment

The template references `greggee/nvpair-container:1.0.0-2` (PAIR 1.0.0,
wrapper revision 2). It must be built locally or published to Docker Hub before
use; changing the template does not publish an image. Start with
a fresh node identity and a unique hostname such as `PAIR-UNRAID`.

The template uses NVIDIA's official 256 x 256 PAIR application icon from the
pinned `v1.0.0` release. This remains an unofficial container wrapper. The original
generated [alternative icon](../assets/nvpair-icon.png) and its
[generation prompt](../assets/nvpair-icon-prompt.txt) are preserved. To use the
alternative, set **Icon URL** in Advanced View to:

```text
https://raw.githubusercontent.com/ggee/nvpair-container/main/assets/nvpair-icon.png
```

The name shown in PAIR comes from the container hostname. In **Advanced View**,
change only `--hostname=PAIR-UNRAID` in **Extra Parameters**, for example to
`--hostname=Tower-AI`, and click **Apply** to recreate the container. Use a unique
hostname with letters, numbers, and hyphens. Unraid's container **Name** field is
separate and does not change the PAIR display name. Keep the same state mapping;
renaming does not require deleting state or creating a new pairing identity.

1. Install/configure Ollama separately. Expose its API on host loopback
   `127.0.0.1:11434`. Configure its NVIDIA compute access separately if needed.
2. Install the XML as a local user template, for example
   `/boot/config/plugins/dockerMan/templates-user/my-nvpair.xml`, then select
   it through **Docker → Add Container**.
3. Select your appdata location, default `/mnt/user/appdata/nvpair`. Docker creates
   a missing directory. Startup automatically assigns the directory to
   `10002:10002` with mode `0700` before starting PAIR as that user. No manual
   `mkdir`, `chown`, or `chmod` is needed on a local filesystem supporting these
   operations. Existing identity files are preserved; ownership is not changed
   recursively. Never use a shared appdata directory or another node's state.
   Create a dedicated `nvpair` share and map **Engine and model storage**
   from `/mnt/user/nvpair` to `/storage`. Startup creates `engines/` and
   `models/llamacpp/`, sets their ownership and permissions, and links the PAIR
   paths to them. The share root's permissions are preserved. This prepares
   storage only; the wrapper still enables only the Ollama proxy. If upgrading
   from the two-mount layout, remove the old engine/model mappings. See
   [storage and migration](../README.md#engine-and-model-storage) for existing
   files; nonempty directories in appdata require manual migration.
4. For an existing installation, use the rebuilt `1.0.0-2` image (pull it once
   published, or load a local build) and replace the old
   **Extra Parameters** with the value in the updated XML. Remove the old
   `--user=10002:10002` flag; preserve `--cap-drop=ALL` and add `CHOWN`, `FOWNER`,
   `DAC_OVERRIDE`, `SETUID`, and `SETGID` with `--cap-add` as in the template.
   These permit initialization and are dropped from the running PAIR process.
   Importing a new template does not update an existing container's settings.
5. Verify host port availability and enforce the trusted-LAN IPv4/IPv6 boundary
   described in the main README before starting. The Ubuntu systemd/firewall
   units are not part of this image. Enable Unraid autostart after validation.
6. For NVIDIA telemetry, install the Nvidia-Driver plugin with a driver compatible
   with your GPU. In Advanced View, append `--gpus=all` to **Extra Parameters**,
   set **NVIDIA GPU selection** (`NVIDIA_VISIBLE_DEVICES`) to `all`, and leave
   **NVIDIA capabilities** (`NVIDIA_DRIVER_CAPABILITIES`) as `utility`. To select
   one GPU instead, use `--runtime=nvidia` with its `GPU-...` UUID, obtained using
   `nvidia-smi --query-gpu=name,uuid --format=csv,noheader`. Preserve the existing
   extra flags. Leave selection at `void` to disable GPU exposure. Apply recreates
   the container so PAIR can detect the GPU at startup. Configure Ollama's compute
   access separately; AMD GPU utilization telemetry is not supported here.
7. Start the container and check its health. Send an invitation from your PAIR
   desktop client. In Unraid's **Docker** tab, click the running **nvpair**
   container's icon and select **Console**. Inside that Console, run:

   ```bash
   python3 /app/admin.py accept
   ```

   Enter the PIN displayed by the inviting PAIR client. To check status in the
   same Console, run:

   ```bash
   python3 /app/admin.py status
   ```

   The Console opens as root for administration; the running PAIR services use
   UID/GID `10002:10002`. These helpers communicate with the existing service.
   Verify a streamed inference request originating from another node.

For telemetry, run this in the container Console, then inspect the node in
Windows PAIR during a short Ollama generation:

```bash
nvidia-smi --query-gpu=name,utilization.gpu,memory.used,memory.total --format=csv
```

Keep read-only rootfs, non-root PAIR workers, the template capabilities and
no-new-privileges unless a specific, diagnosed host compatibility issue requires
a change.

[Unraid container settings reference](https://docs.unraid.net/go/docker-management/).
This template has XML checks but has not been installed on Unraid yet.
