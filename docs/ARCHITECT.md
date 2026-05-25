# Architecture

kleys is organized into focused modules that handle distinct concerns: CLI argument parsing, keyring interaction, encryption, and process execution.

## Module Structure

```mermaid
graph TD
    cli["cli.py<br/>(entry, arg parse)"] --> modes["modes.py<br/>(orchestrator)"]
    cli --> keyring["keyring_.py<br/>(keyring API)"]
    cli --> crypto["crypto.py<br/>(Fernet)"]
    
    modes --> keyring
    modes --> crypto
    modes --> utils["utils.py<br/>(temp file, cleanup)"]
    modes --> console["console.py<br/>(output)"]
    modes --> password["password.py<br/>(password resolution)"]
    
    keyring --> keyring_lib["keyring library"]
    utils --> os["os / tempfile"]
    crypto --> pbkdf2["PBKDF2-HMAC-SHA256"]
    crypto --> fernet["Fernet<br/>AES-128-CBC + HMAC"]
    password --> typer["typer.prompt"]
    
    style cli fill:#e1f5ff
    style modes fill:#f3e5f5
    style keyring fill:#fce4ec
    style crypto fill:#fce4ec
    style utils fill:#fff3e0
    style password fill:#e8f5e9
```

### Module responsibilities

| Module | Role |
|--------|------|
| **cli.py** | Entry point (`kleys.cli:main`). Manual arg parsing. Routes to `run`/`show`/`clear` handlers. |
| **modes.py** | **Orchestrator.** `dispatch()` handles: file import, keyring lookup (3-phase), mode selection, subprocess execution. |
| **keyring_.py** | Thin wrapper over `keyring` library. Stores all entries under fixed username `"__secrets__"`. |
| **crypto.py** | Fernet encryption (AES-128-CBC + HMAC-SHA256). PBKDF2: SHA256, 600K iterations, random 16-byte salt. |
| **password.py** | Password resolution: `--password` > `KLEYS_PASSWORD` env > interactive prompt. Encrypt confirms twice; decrypt once. |
| **utils.py** | Temp file creation (`chmod 600`) and cleanup via `atexit` + signal handlers (`SIGINT`, `SIGTERM`). |
| **console.py** | Output styling: `info`, `success`, `warn`, `error`, `cmd` using `typer.secho`. |

## Secrets Routing: Per-Mode Data Flow

Each mode has a different path for secrets through the system.

### File Mode (default)

```mermaid
sequenceDiagram
    participant K as Keyring
    participant M as Memory
    participant D as Disk
    participant P as Subprocess
    
    M->>M: decrypt if encrypted
    M->>D: write temp .env<br/>chmod 0600
    D->>P: subprocess reads<br/>SECRETS_FILE path
    P-->>D: process running
    D->>M: atexit/signal<br/>os.remove
```

**Exposure:** Temp file on disk only while subprocess runs. Permissions `600` (owner-only).

### File Descriptor Mode (`@SECRETS@`)

```mermaid
sequenceDiagram
    participant K as Keyring
    participant M as Memory
    participant P as Subprocess
    
    M->>M: decrypt if encrypted
    M->>M: os.pipe() → (r_fd, w_fd)
    M->>M: daemon thread writes to w_fd
    M->>P: subprocess via pass_fds=(r_fd)
    P->>P: reads from /dev/fd/r_fd
    M->>M: close fds, join thread
```

**Exposure:** Zero disk I/O. In-memory pipe only. Unix only; Windows exits with error.

### Export Mode (`--export`)

```mermaid
sequenceDiagram
    participant K as Keyring
    participant M as Memory
    participant E as Env
    participant P as Subprocess
    
    M->>M: decrypt if encrypted
    M->>M: parse KEY=VALUE lines
    M->>E: merge into subprocess env dict
    E->>P: subprocess inherits env
```

**Exposure:** Zero disk I/O. Secrets in subprocess environment only. Works on all platforms.

## Keyring Lookup (3-phase)

On `run` with no existing entry in keyring:

1. **Phase 1:** Look up `{app}-encrypted` entry
2. **Phase 2:** Look up `{app}` entry (plaintext fallback)
3. **Phase 3:** Neither found → interactive stdin prompt, store result

Once stored, subsequent runs load directly from keyring without prompting.

## Cleanup & Signal Handling

The `setup_cleanup()` function ensures temp files are deleted even if the subprocess crashes:

```python
atexit.register(cleanup)           # Normal exit
signal.signal(SIGINT, cleanup)     # Ctrl-C
signal.signal(SIGTERM, cleanup)    # Kill signal
```

---

For security details, threat model, and encryption protocol, see [SECURITY.md](SECURITY.md).
