import keyring as _keyring
import keyring.errors

_SERVICE_USER = "__secrets__"


def store(service: str, secret: str) -> None:
    _keyring.set_password(service, _SERVICE_USER, secret)


def lookup(service: str) -> str | None:
    try:
        return _keyring.get_password(service, _SERVICE_USER)
    except keyring.errors.KeyringError:
        return None


def delete(service: str) -> bool:
    try:
        _keyring.delete_password(service, _SERVICE_USER)
        return True
    except keyring.errors.PasswordDeleteError:
        return False
