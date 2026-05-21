import os
import subprocess
import sys
import threading
from pathlib import Path

import typer

from kleys import console, crypto
from kleys import keyring_ as kr
from kleys.keyring_ import KeyringUnavailableError
from kleys.password import (
    resolve_decrypt_password,
    resolve_encrypt_password,
)
from kleys.utils import create_temp_env, setup_cleanup


def _parse_env(content: str) -> dict[str, str]:
    env: dict[str, str] = {}
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        if key:
            env[key] = value
    return env


def _offer_store_file(
    file: str, app_name: str, password: str | None, plaintext_mode: bool
) -> bool:
    console.info(f"\u2139 Found existing local file: {file}")
    try:
        answer = typer.prompt(
            f"Store this file in the keyring for app='{app_name}'? (y/n)"
        )
    except typer.Abort:
        return False
    if not answer.lower().startswith("y"):
        return False
    with open(file) as f:
        content = f.read()
    if plaintext_mode:
        try:
            kr.store(app_name, content)
        except KeyringUnavailableError:
            console.error(
                "Error: No keyring backend is available. Kleys requires a"
                " system keyring to operate.\n"
                "  Install a keyring backend (try: pip install keyrings.alt),\n"
                "  or on Linux: apt install python3-secretstorage"
            )
            sys.exit(1)
        console.success(
            f"\u2713 Stored in keyring as '{app_name}' (not encrypted)"
        )
    else:
        pw = resolve_encrypt_password(password)
        if pw is None:
            console.error(
                "Error: No password available for encryption."
                " Use --plaintext, SECRET_TOOL_PASSWORD, or"
                " --password PASSWORD."
            )
            sys.exit(1)
        encrypted = crypto.encrypt(content, pw)
        try:
            kr.store(f"{app_name}-encrypted", encrypted)
        except KeyringUnavailableError:
            console.error(
                "Error: No keyring backend is available. Kleys requires a"
                " system keyring to operate.\n"
                "  Install a keyring backend (try: pip install keyrings.alt),\n"
                "  or on Linux: apt install python3-secretstorage"
            )
            sys.exit(1)
        console.success(f"\u2713 Stored in keyring as '{app_name}' (encrypted)")
    return True


def _load_secrets(
    app_name: str,
    password: str | None,
    plaintext_mode: bool,
) -> str:
    encrypted_key = f"{app_name}-encrypted"
    if not plaintext_mode:
        encrypted_content = kr.lookup(encrypted_key)
        if encrypted_content is not None:
            pw = resolve_decrypt_password(password)
            if pw is None:
                console.error(
                    "Error: Encrypted entry found but no password"
                    " available. Use --password=PASSWORD or set"
                    " SECRET_TOOL_PASSWORD."
                )
                sys.exit(1)
            decrypted = crypto.decrypt(encrypted_content, pw)
            if decrypted is None:
                console.error(
                    "Error: Decryption failed. Wrong password or"
                    " corrupted data."
                )
                sys.exit(1)
            return decrypted
    plain_content = kr.lookup(app_name)
    if plain_content is not None:
        if not plaintext_mode:
            console.info(
                f"\u2139 Found plaintext entry for app="
                f"'{app_name}' \u2014 unencrypted"
            )
        return plain_content
    console.warn(f"\u26a0 No secrets found for app='{app_name}' in keyring.")
    console.info("Paste secrets content (KEY=VALUE), then press Ctrl-D:")
    console.info("(Press Ctrl-C to cancel)")
    secrets_input = sys.stdin.read()
    if not secrets_input:
        console.error("Error: No secrets provided. Aborting.")
        sys.exit(1)
    if plaintext_mode:
        try:
            kr.store(app_name, secrets_input)
        except KeyringUnavailableError:
            console.error(
                "Error: No keyring backend is available. Kleys requires a"
                " system keyring to operate.\n"
                "  Install a keyring backend (try: pip install keyrings.alt),\n"
                "  or on Linux: apt install python3-secretstorage"
            )
            sys.exit(1)
        console.success(
            f"\u2713 Stored in keyring as '{app_name}' (not encrypted)"
        )
    else:
        pw = resolve_encrypt_password(password)
        if pw is None:
            console.error(
                "Error: No password available for encryption."
                " Use --plaintext, SECRET_TOOL_PASSWORD, or"
                " --password PASSWORD."
            )
            sys.exit(1)
        encrypted = crypto.encrypt(secrets_input, pw)
        try:
            kr.store(f"{app_name}-encrypted", encrypted)
        except KeyringUnavailableError:
            console.error(
                "Error: No keyring backend is available. Kleys requires a"
                " system keyring to operate.\n"
                "  Install a keyring backend (try: pip install keyrings.alt),\n"
                "  or on Linux: apt install python3-secretstorage"
            )
            sys.exit(1)
        console.success(f"\u2713 Stored in keyring as '{app_name}' (encrypted)")
    return secrets_input


def _exec_file(command: list[str], secrets_content: str, file: str) -> int:
    path = create_temp_env(secrets_content)
    console.cmd(f"\u2192 Running: {' '.join(command)}")
    env = {**os.environ, "SECRETS_FILE": path}
    try:
        result = subprocess.run(command, env=env)
    except FileNotFoundError:
        console.error(
            f"Error: Command not found: {command[0]!r}.\n"
            "  Use --source to source variables into the environment,\n"
            "  wrap in sh -c '<command>' for shell built-ins,\n"
            "  or specify a valid executable."
        )
        return 127
    return result.returncode


def _exec_source(command: list[str], secrets_content: str) -> int:
    parsed = _parse_env(secrets_content)
    env = {**os.environ, **parsed}
    console.cmd(f"\u2192 Running: {' '.join(command)}")
    try:
        result = subprocess.run(command, env=env)
    except FileNotFoundError:
        console.error(
            f"Error: Command not found: {command[0]!r}.\n"
            "  Make sure the command is installed and on PATH,\n"
            "  or wrap in sh -c '<command>' for shell built-ins."
        )
        return 127
    return result.returncode


def _exec_fd(command: list[str], secrets_content: str) -> int:
    r_fd, w_fd = os.pipe()

    def _writer() -> None:
        try:
            os.write(w_fd, secrets_content.encode("utf-8"))
        finally:
            os.close(w_fd)

    t = threading.Thread(target=_writer, daemon=True)
    t.start()
    fd_path = f"/dev/fd/{r_fd}"
    modified_args = [arg.replace("@SECRETS@", fd_path) for arg in command]
    console.cmd(f"\u2192 Running: {' '.join(modified_args)}")
    try:
        result = subprocess.run(
            modified_args,
            env={**os.environ, "SECRETS_FILE": fd_path},
            pass_fds=(r_fd,),
        )
    finally:
        os.close(r_fd)
        t.join()
    return result.returncode


def dispatch(
    command: list[str],
    file: str,
    app_name: str,
    source_mode: bool,
    password: str | None,
    plaintext_mode: bool,
) -> None:
    setup_cleanup()
    resolved_app = app_name if app_name else Path.cwd().name
    use_fd = any("@SECRETS@" in arg for arg in command)
    if not use_fd and os.path.exists(file):
        if _offer_store_file(file, resolved_app, password, plaintext_mode):
            os.remove(file)
        else:
            if source_mode:
                env = {**os.environ, **_parse_env(Path(file).read_text())}
                console.cmd(f"\u2192 Running: {' '.join(command)}")
                subprocess.run(command, env=env)
            else:
                env = {**os.environ, "SECRETS_FILE": os.path.abspath(file)}
                console.cmd(f"\u2192 Running: {' '.join(command)}")
                subprocess.run(command, env=env)
            return
    secrets_content = _load_secrets(resolved_app, password, plaintext_mode)
    if use_fd:
        if sys.platform == "win32":
            console.error(
                "Error: @SECRETS@ (FD mode) is not supported on Windows."
                " Use --source or file mode instead."
            )
            sys.exit(1)
        sys.exit(_exec_fd(command, secrets_content))
    elif source_mode:
        sys.exit(_exec_source(command, secrets_content))
    else:
        sys.exit(_exec_file(command, secrets_content, file))
