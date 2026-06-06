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
| **modes.py** | **Orchestrator.** `dispatch()` handles: file import (Phase 0), keyring lookup (Phases 1–3), mode selection, subprocess execution. |
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
    
    K->>M: kr.lookup()
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
    
    K->>M: kr.lookup()
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
    
    K->>M: kr.lookup()
    M->>M: decrypt if encrypted
    M->>M: parse KEY=VALUE lines
    M->>E: merge into subprocess env dict
    E->>P: subprocess inherits env
```

**Exposure:** Zero disk I/O. Secrets in subprocess environment only. Works on all platforms.

## Dispatch Decision Flow

`dispatch()` in `modes.py` is the orchestrator. The flowchart below covers the full decision tree:

```mermaid
flowchart TD
    Start["dispatch() called"] --> CmdCheck{"command empty?"}
    CmdCheck -- yes --> Exit1["sys.exit(1)"]
    CmdCheck -- no --> ResolveApp["resolve app name"]
    ResolveApp --> FDCheck{"@SECRETS@ in<br/>command args?"}
    FDCheck -- yes --> LoadSecrets["_load_secrets()"]
    FDCheck -- no --> EnvExists{".env file<br/>exists?"}
    EnvExists -- yes --> OfferImport["_offer_store_file()<br/>'Store in keyring?'"]
    OfferImport -- "yes" --> RemoveEnv["os.remove(.env)<br/>import into keyring"]
    OfferImport -- "no" --> OverwriteCheck{"source_mode?"}
    RemoveEnv --> LoadSecrets
    OverwriteCheck -- "yes (export)" --> LoadSecrets
    OverwriteCheck -- "no (file)" --> WarnOverwrite["warn: .env will<br/>be overwritten"]
    WarnOverwrite --> ConfirmOverwrite{"Continue?"}
    ConfirmOverwrite -- "no / Abort" --> Exit1
    ConfirmOverwrite -- "yes" --> LoadSecrets
    EnvExists -- no --> LoadSecrets

    LoadSecrets --> ModeSelect{"mode?"}
    ModeSelect -- "fd" --> ExecFD["_exec_fd()<br/>pipe + subprocess"]
    ModeSelect -- "source" --> ExecSource["_exec_source()<br/>export as env vars"]
    ModeSelect -- "file" --> ExecFile["_exec_file()<br/>temp file + subprocess"]

    ExecFD --> Done["sys.exit(code)"]
    ExecSource --> Done
    ExecFile --> Done
```

## Secrets Sourcing (4-phase)

Secrets are resolved in `_load_secrets()` after the `.env` import decision:

```mermaid
flowchart TD
    subgraph Phase0["Phase 0 — .env import (preface)"]
        EnvImport["dispatch() asks:<br/>'Store .env in keyring?'"]
        EnvImport -- yes --> ImportStore["store .env in keyring<br/>os.remove(.env)"]
        EnvImport -- no --> Fallthrough["fall through to<br/>_load_secrets()"]
        ImportStore --> Fallthrough
    end

    subgraph Phases1to3["Phases 1–3 — keyring lookup + fallback"]
        P1["Phase 1:<br/>kr.lookup('{app}-encrypted')"]
        P1 -- "found" --> Decrypt["resolve password<br/>crypto.decrypt()"]
        P1 -- "not found" --> P2["Phase 2:<br/>kr.lookup('{app}')"]
        P2 -- "found" --> ReturnPlain["return plaintext"]
        P2 -- "not found" --> P3["Phase 3:<br/>prompt user to paste"]
        P3 --> StoreInKeyring["store in keyring"]
        Decrypt --> Return["return secrets"]
        ReturnPlain --> Return
        StoreInKeyring --> Return
    end

    Fallthrough --> P1
```

1. **Phase 0 — `.env` import (preface):** If a `.env` file exists and is not in FD mode, the user is asked whether to import it into the keyring. On "yes", the file is stored, removed, and execution falls through to normal keyring lookup. On "no", the `.env` file is ignored and execution also falls through to normal keyring lookup (in file mode, a warning is shown before overwriting the existing `.env`).

2. **Phase 1 — Encrypted lookup:** Look up `{app}-encrypted` in the keyring. If found, resolve the decryption password and decrypt.

3. **Phase 2 — Plaintext fallback:** Look up `{app}` (plaintext). If found, return it (with a warning if encryption is the default).

4. **Phase 3 — Interactive paste:** Neither found → prompt the user to paste secrets via stdin, store them in the keyring, and return.

Once stored, subsequent runs resolve from Phase 1 or 2 directly without prompting — unless a local `.env` file triggers Phase 0 again.

## Cleanup & Signal Handling

The `setup_cleanup()` function ensures temp files are deleted even if the subprocess crashes:

```python
atexit.register(cleanup)           # Normal exit
signal.signal(SIGINT, cleanup)     # Ctrl-C
signal.signal(SIGTERM, cleanup)    # Kill signal
```

---

For security details, threat model, and encryption protocol, see [SECURITY.md](SECURITY.md).
