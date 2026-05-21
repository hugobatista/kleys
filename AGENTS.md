# AGENTS.md — kleys

## Commands

```bash
hatch run test      # pytest src tests --cov=src/kleys --cov-fail-under=100 -v
hatch run typecheck # mypy src --strict --no-incremental
hatch run validate  # lint → format-check → test → typecheck
```

## Entrypoint

`kleys.cli:main` → manual arg parsing → subcommand dispatcher.

Three subcommands:
- **run** — execute a command with secrets (file/source/FD modes)
- **show** — display all stored secrets for an app
- **clear** — delete all stored secrets for an app

CLI parsing is manual (not Typer decorators). Typer used only for `prompt`/`secho`.

## Testing

`conftest.py` auto-mocks `keyring`, `subprocess.run`, `atexit.register`, `signal.signal`. No test touches real keyring or subprocess.

Must call `subprocess.run.reset_mock()` before each test that inspects it (shared mock). FD mode tests must mock `os.pipe` returning specific FDs like `(10, 11)`.
