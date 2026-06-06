import os
import sys
from typing import cast

import typer

from kleys.console import error


def resolve_encrypt_password(explicit: str | None) -> str | None:
    if explicit:
        return explicit
    env_pw = os.environ.get("KLEYS_PASSWORD")
    if env_pw:
        return env_pw
    if not sys.stdin.isatty():
        return None
    while True:
        pw = cast(
            str, typer.prompt("Enter encryption password", hide_input=True)
        )
        typer.echo("")
        if not pw:
            error("Error: Password cannot be empty.")
            continue
        confirm = cast(str, typer.prompt("Confirm password", hide_input=True))
        typer.echo("")
        if pw != confirm:
            error("Error: Passwords do not match.")
            continue
        return pw


def resolve_decrypt_password(explicit: str | None) -> str | None:
    if explicit:
        return explicit
    env_pw = os.environ.get("KLEYS_PASSWORD")
    if env_pw:
        return env_pw
    if not sys.stdin.isatty():
        return None
    pw = cast(str, typer.prompt("Enter decryption password", hide_input=True))
    typer.echo("")
    if not pw:
        return None
    return pw
