import sys

import keyring as _keyring
import keyring.errors

_SERVICE_USER = "__secrets__"


class KeyringUnavailableError(RuntimeError):
    pass


def keyring_install_hint() -> str:
    hint = "  Install a keyring backend (try: pip install keyrings.alt)"
    if sys.platform == "linux":
        hint += ",\n  or on Debian/Ubuntu: apt install python3-secretstorage"
    return hint


def store(service: str, secret: str) -> None:
    try:
        _keyring.set_password(service, _SERVICE_USER, secret)
    except keyring.errors.KeyringError as exc:
        raise KeyringUnavailableError(
            "No keyring backend is available. Kleys requires a system"
            f" keyring to operate.\n{keyring_install_hint()}"
        ) from exc


def lookup(service: str) -> str | None:
    try:
        return _keyring.get_password(service, _SERVICE_USER)
    except keyring.errors.KeyringError:
        return None


def delete(service: str) -> bool:
    try:
        _keyring.delete_password(service, _SERVICE_USER)
        return True
    except keyring.errors.KeyringError:
        return False
