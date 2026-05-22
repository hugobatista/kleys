import sys
from typing import Any

from kleys import __version__, crypto, modes
from kleys import keyring_ as kr
from kleys.console import error, info, success, warn
from kleys.modes import resolve_app_name
from kleys.password import resolve_decrypt_password

_TOP_HELP = """\
Usage: kleys [OPTIONS] COMMAND [ARGS...]

  Execute commands with secrets loaded from your system keyring.

Commands:
  run     Execute a command with secrets from the keyring
  show    Display all stored secrets for an app
  clear   Delete all stored secrets for an app

Use 'kleys run --help' for run options.
Use 'kleys show --help' for show options.
Use 'kleys clear --help' for clear options.
"""

_VERSION_HELP = """\
kleys {version}
"""


def _top_help() -> str:
    return f"kleys {__version__}\n\n{_TOP_HELP}"

_RUN_HELP = """\
Usage: kleys run [OPTIONS] COMMAND [ARGS...]

  Execute a command with secrets loaded from your system keyring.

  Avoids storing .env files on disk by loading secrets encrypted from
  the system keyring (GNOME Keyring, KWallet, macOS Keychain, Windows
  Credential Manager) and passing them to your command via temp file,
  environment variables, or file descriptor.

Options:
  --file FILE, -f FILE    Secrets file path (default: .env)
  --app APP, -a APP       Keyring app identifier (default: current folder name)
  --source, -s            Source and export .env vars into the environment
  --password PASSWORD     Encrypt secrets with a password (AES-256-CBC).
                          If PASSWORD is omitted, resolves from
                          KLEYS_PASSWORD env var or prompts.
  --plaintext             Disable encryption, store/retrieve secrets as
                          plaintext (default: encryption is enabled).
  --help, -h              Show this help message

Examples:
  kleys run uv run pywrangler dev
  kleys run --source ansible-playbook site.yml
  kleys run act --secret-file @SECRETS@
  kleys run --file .secrets act --secret-file .secrets
  kleys run --app myproject-prod npm start
"""

_SHOW_HELP = """\
Usage: kleys show [OPTIONS]

  Display all stored secrets for an app.

  Loads secrets from the system keyring for the given app and prints
  them to stdout. Tries encrypted entry first, falls back to plaintext.

Options:
  --app APP, -a APP       Keyring app identifier (default: current folder name)
  --password PASSWORD     Decryption password (required if encrypted)
  --help, -h              Show this help message
"""

_CLEAR_HELP = """\
Usage: kleys clear [OPTIONS]

  Delete all stored secrets for an app.

  Removes both encrypted and plaintext entries from the system keyring.

Options:
  --app APP, -a APP       Keyring app identifier (default: current folder name)
  --force                 Skip confirmation prompt
  --help, -h              Show this help message
"""


def _parse_options(args: list[str]) -> tuple[dict[str, Any], list[str]]:
    opts = {
        "file": ".env",
        "app_name": None,
        "source_mode": False,
        "password": None,
        "plaintext_mode": False,
    }
    i = 0
    while i < len(args):
        a = args[i]
        if a in ("--help", "-h"):
            sys.stdout.write(_RUN_HELP)
            sys.exit(0)
        elif a in ("--file", "-f"):
            if i + 1 >= len(args):
                error("error: --file requires a value")
                sys.exit(1)
            opts["file"] = args[i + 1]
            i += 2
        elif a in ("--app", "-a"):
            if i + 1 >= len(args):
                error("error: --app requires a value")
                sys.exit(1)
            opts["app_name"] = args[i + 1]
            i += 2
        elif a in ("--source", "-s"):
            opts["source_mode"] = True
            i += 1
        elif a == "--password":
            if i + 1 >= len(args):
                error("error: --password requires a value")
                sys.exit(1)
            warn(
                "Warning: --password is visible in process listings (ps aux)."
                " Use KLEYS_PASSWORD env var or interactive prompt instead."
            )
            opts["password"] = args[i + 1]
            i += 2
        elif a == "--plaintext":
            opts["plaintext_mode"] = True
            i += 1
        else:
            break
    return opts, args[i:]


def _parse_show_options(args: list[str]) -> dict[str, Any]:
    opts: dict[str, Any] = {
        "app_name": None,
        "password": None,
    }
    i = 0
    while i < len(args):
        a = args[i]
        if a in ("--help", "-h"):
            sys.stdout.write(_SHOW_HELP)
            sys.exit(0)
        elif a in ("--app", "-a"):
            if i + 1 >= len(args):
                error("error: --app requires a value")
                sys.exit(1)
            opts["app_name"] = args[i + 1]
            i += 2
        elif a == "--password":
            if i + 1 >= len(args):
                error("error: --password requires a value")
                sys.exit(1)
            warn(
                "Warning: --password is visible in process listings (ps aux)."
                " Use KLEYS_PASSWORD env var or interactive prompt instead."
            )
            opts["password"] = args[i + 1]
            i += 2
        else:
            error(f"error: unknown option {a!r}")
            sys.exit(1)
    return opts


def _parse_clear_options(args: list[str]) -> dict[str, Any]:
    opts: dict[str, Any] = {
        "app_name": None,
        "force": False,
    }
    i = 0
    while i < len(args):
        a = args[i]
        if a in ("--help", "-h"):
            sys.stdout.write(_CLEAR_HELP)
            sys.exit(0)
        elif a in ("--app", "-a"):
            if i + 1 >= len(args):
                error("error: --app requires a value")
                sys.exit(1)
            opts["app_name"] = args[i + 1]
            i += 2
        elif a == "--force":
            opts["force"] = True
            i += 1
        else:
            error(f"error: unknown option {a!r}")
            sys.exit(1)
    return opts


def _handle_run(args: list[str]) -> None:
    opts, command = _parse_options(args)
    opts["app_name"] = resolve_app_name(opts["app_name"])
    opts["command"] = command
    modes.dispatch(**opts)


def _handle_show(args: list[str]) -> None:
    opts = _parse_show_options(args)
    app_name = resolve_app_name(opts["app_name"])

    encrypted_key = f"{app_name}-encrypted"
    encrypted_content = kr.lookup(encrypted_key)
    if encrypted_content is not None:
        password = resolve_decrypt_password(opts["password"])
        if password is None:
            error(
                "Error: Encrypted entry found but no password"
                " available. Use --password=PASSWORD or set"
                " KLEYS_PASSWORD."
            )
            sys.exit(1)
        secrets = crypto.decrypt(encrypted_content, password)
        if secrets is None:
            error("Error: Decryption failed. Wrong password or corrupted data.")
            sys.exit(1)
        info(f"Secrets for '{app_name}':")
        info(secrets)
        return

    plain_content = kr.lookup(app_name)
    if plain_content is not None:
        info(f"Secrets for '{app_name}' (plaintext):")
        info(plain_content)
        return

    warn(f"No secrets found for app='{app_name}' in keyring.")
    sys.exit(1)


def _handle_clear(args: list[str]) -> None:
    opts = _parse_clear_options(args)
    app_name = resolve_app_name(opts["app_name"])

    if not opts["force"]:
        if not sys.stdin.isatty():
            error(
                "Error: Confirmation required. Use --force to skip prompt"
                " in non-interactive mode."
            )
            sys.exit(1)
        import typer

        try:
            confirmed = typer.confirm(
                f"Danger: This will delete all secrets for '{app_name}'. Continue?"
            )
        except typer.Abort:
            confirmed = False
        if not confirmed:
            warn("Clear cancelled.")
            sys.exit(1)

    deleted_any = False
    if kr.delete(f"{app_name}-encrypted"):
        success(f"Deleted encrypted secrets for '{app_name}'")
        deleted_any = True
    if kr.delete(app_name):
        success(f"Deleted plaintext secrets for '{app_name}'")
        deleted_any = True

    if not deleted_any:
        warn(f"No secrets found for app='{app_name}' in keyring.")
        sys.exit(1)


def main(argv: list[str] | None = None) -> None:
    args = argv if argv is not None else sys.argv[1:]

    if not args:
        sys.stdout.write(_top_help())
        sys.exit(1)

    if args[0] in ("--version", "-V"):
        sys.stdout.write(_VERSION_HELP.format(version=__version__))
        sys.exit(0)

    if args[0] in ("--help", "-h"):
        sys.stdout.write(_top_help())
        sys.exit(0)

    subcommand = args[0]
    remaining = args[1:]

    if subcommand == "run":
        _handle_run(remaining)
    elif subcommand == "show":
        _handle_show(remaining)
    elif subcommand == "clear":
        _handle_clear(remaining)
    else:
        _handle_run(args)


if __name__ == "__main__":
    main()
