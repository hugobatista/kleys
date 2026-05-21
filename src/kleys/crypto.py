import base64
import os

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

SALT_LENGTH = 16
KEY_LENGTH = 32
ITERATIONS = 600_000


def _derive_key(password: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=KEY_LENGTH,
        salt=salt,
        iterations=ITERATIONS,
    )
    return kdf.derive(password.encode("utf-8"))


def encrypt(plaintext: str, password: str) -> str:
    salt = os.urandom(SALT_LENGTH)
    key = _derive_key(password, salt)
    f = Fernet(base64.urlsafe_b64encode(key))
    token = f.encrypt(plaintext.encode("utf-8"))
    salt_b64 = base64.b64encode(salt).decode("ascii")
    return salt_b64 + ":" + token.decode("ascii")


def decrypt(payload: str, password: str) -> str | None:
    try:
        salt_b64, token = payload.split(":", 1)
        salt = base64.b64decode(salt_b64)
        key = _derive_key(password, salt)
        f = Fernet(base64.urlsafe_b64encode(key))
        return f.decrypt(token.encode("utf-8")).decode("utf-8")
    except Exception:
        return None
