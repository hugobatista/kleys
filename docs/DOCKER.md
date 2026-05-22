## Docker

The image ships with **two keyring backends**: `keyrings.alt` (file-backed, standalone) and `python3-secretstorage` (D-Bus, connects to host keyring). Choose your workflow at `docker run`:

| Workflow | Run command | Persistence |
|----------|-------------|-------------|
| **Standalone** — file-backed keyring inside the container | `-v kleys-data:/app/data` | Named volume, auto-created on first run |
| **Host keyring** — uses your machine's GNOME Keyring / KWallet | `-v /run/user/$(id -u)/bus:/run/user/$(id -u)/bus -e DBUS_SESSION_BUS_ADDRESS=...` | Host keyring |

Build:

```bash
docker build -t kleys .
```

**Standalone workflow** (Docker volume persists secrets across container runs):

```bash
# First run — paste secrets, stored in the volume-backed keyring file
docker run --rm -it -v kleys-data:/app/data kleys run --key test --export printenv var1

# Subsequent runs — same volume, secrets already stored
docker run --rm -it -v kleys-data:/app/data kleys run --key test --export printenv var1
```

The named volume `kleys-data` is auto-created by Docker. Secrets survive container removal (`--rm`).

**Host keyring workflow** (mount D-Bus socket to use your system keyring):

```bash
docker run --rm -it \
  --user $(id -u):$(id -g) \
  --security-opt label=type:spc_t \
  -v /run/user/$(id -u)/bus:/run/user/$(id -u)/bus \
  -e DBUS_SESSION_BUS_ADDRESS="unix:path=/run/user/$(id -u)/bus" \
  kleys run --key test --export printenv var1
```

> **Linux only.** D-Bus is a Linux IPC mechanism — this does not work on Docker Desktop for macOS or Windows. Requires a running secret service provider on the host (GNOME Keyring, KWallet, or KeepassXC with Secret Service plugin). The container user (`--user`) must match your host UID for D-Bus authentication to succeed. On SELinux distros (Fedora, RHEL, CentOS), use `--security-opt label=type:spc_t` — it grants the container the `spc_t` type, which allows D-Bus socket access while keeping SELinux enabled.

No volume needed — reads and writes your host's GNOME Keyring or KWallet directly.

**Non-interactive commands** work with either workflow:

```bash
docker run --rm kleys show --help
docker run --rm kleys clear --key test
```

## File descriptor mode with Docker

Use `@SECRETS@` with `--env-file` to pass secrets from keyring directly to a container — zero disk I/O:

```bash
kleys docker run --env-file @SECRETS@ myimage
```
