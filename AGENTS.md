# AGENTS.md — kleys

## Commands

```bash
uv run hatch run test      # runs pytest (config in pyproject.toml)
uv run hatch run typecheck # runs mypy (config in pyproject.toml)
uv run hatch run validate  # lint → format-check → test → typecheck
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

Must call "uv run hatch run validate" to run all tests, including type checks and linting, after implementing a new feature or fixing a bug. 
