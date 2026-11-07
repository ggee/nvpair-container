# Unraid deployment

This template is for local installation; the image is not published. Start with
a fresh node identity and a unique hostname such as `PAIR-UNRAID`.

1. Install/configure Ollama separately. Expose its API on host loopback
   `127.0.0.1:11434`. If it should use the GTX 1080, configure its NVIDIA compute
   access separately and verify GPU inference first.
2. Build this image on a Linux/amd64 Docker host with `docker compose build`.
   If that host is not Unraid, transfer it using:

   ```bash
   docker save -o nvpair-container-1.0.0.tar nvpair-container:1.0.0
   # Transfer the archive to Unraid, then on Unraid:
   docker load -i nvpair-container-1.0.0.tar
   ```

3. Create `/mnt/user/appdata/nvpair`, set owner `10002:10002` and mode `0700`.
   Select your preferred appdata location rather than assuming a cache pool.
4. Install the XML as a local user template, for example
   `/boot/config/plugins/dockerMan/templates-user/my-nvpair.xml`, then select
   it through **Docker → Add Container**. Keep the local image repository value;
   there is no remote image for Unraid to pull or auto-update.
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
Keep read-only rootfs, non-root UID, dropped capabilities and no-new-privileges
unless a specific, diagnosed host compatibility issue requires a change.

[Unraid container settings reference](https://docs.unraid.net/go/docker-management/).
This template has XML checks but has not been installed on Unraid yet.
