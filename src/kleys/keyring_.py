import os
import sys

import keyring as _keyring
import keyring.errors

_SERVICE_PREFIX = "kleys:"
_USERNAME = "secrets"
_APPLICATION_ID = "kleys"

os.environ["KEYRING_PROPERTY_APPID"] = _APPLICATION_ID


class KeyringUnavailableError(RuntimeError):
    pass


def keyring_install_hint() -> str:
    hint = "  Install a keyring backend (try: pip install keyrings.alt)"
    if sys.platform == "linux":
        hint += ",\n  or on Debian/Ubuntu: apt install python3-secretstorage"
    return hint


def store(app_name: str, secret: str) -> None:
    try:
        _keyring.set_password(f"{_SERVICE_PREFIX}{app_name}", _USERNAME, secret)
    except keyring.errors.KeyringError as exc:
        raise KeyringUnavailableError(
            "No keyring backend is available. Kleys requires a system"
            f" keyring to operate.\n{keyring_install_hint()}"
        ) from exc


def lookup(app_name: str) -> str | None:
    try:
        return _keyring.get_password(f"{_SERVICE_PREFIX}{app_name}", _USERNAME)
    except keyring.errors.KeyringError:
        return None


def delete(app_name: str) -> bool:
    try:
        _keyring.delete_password(f"{_SERVICE_PREFIX}{app_name}", _USERNAME)
        return True
    except keyring.errors.KeyringError:
        return False
