# Unraid deployment

The template uses `greggee/nvpair-container:1.0.0` from Docker Hub. Start with
a fresh node identity and a unique hostname such as `PAIR-UNRAID`.

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
4. For an existing installation, pull the rebuilt `1.0.0` image and replace the old
   **Extra Parameters** with the value in the updated XML. Remove the old
   `--user=10002:10002` flag; preserve `--cap-drop=ALL` and add `CHOWN`, `FOWNER`,
   `DAC_OVERRIDE`, `SETUID`, and `SETGID` with `--cap-add` as in the template.
   These permit initialization and are dropped from the running PAIR process.
   Importing a new template does not update an existing container's settings.
5. Verify host port availability and enforce the trusted-LAN IPv4/IPv6 boundary
   described in the main README before starting. The Ubuntu systemd/firewall
   units are not part of this image. Enable Unraid autostart after validation.
6. For NVIDIA telemetry, install the Nvidia-Driver plugin with a GTX 1080
   compatible driver. In advanced template settings add `--runtime=nvidia` to
   **Extra Parameters**, set `NVIDIA_VISIBLE_DEVICES` to the card's UUID, and
   leave `NVIDIA_DRIVER_CAPABILITIES=utility`. Preserve the existing extra flags.
7. Start, check health, accept the invitation as described in the main README,
   and verify a streamed inference request originating from another node.

Verify telemetry in the running container with the `nvidia-smi` query in the main
README, then inspect the node in Windows PAIR during a short Ollama generation.
Keep read-only rootfs, non-root PAIR workers, the template capabilities and
no-new-privileges unless a specific, diagnosed host compatibility issue requires
a change.

[Unraid container settings reference](https://docs.unraid.net/go/docker-management/).
This template has XML checks but has not been installed on Unraid yet.
