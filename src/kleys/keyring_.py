import keyring as _keyring
import keyring.errors

_SERVICE_USER = "__secrets__"


class KeyringUnavailableError(RuntimeError):
    pass


def store(service: str, secret: str) -> None:
    try:
        _keyring.set_password(service, _SERVICE_USER, secret)
    except keyring.errors.KeyringError as exc:
        raise KeyringUnavailableError(
            "No keyring backend available.\n"
            "  Install a keyring backend, or use --file PATH and mount the file into the container."
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
