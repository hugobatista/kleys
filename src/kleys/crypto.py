import base64
import os

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

SALT_LENGTH = 16
KEY_LENGTH = 32
IV_LENGTH = 16
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
    iv = os.urandom(IV_LENGTH)
    key = _derive_key(password, salt)
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
    encryptor = cipher.encryptor()
    data = plaintext.encode("utf-8")
    pad_len = 16 - (len(data) % 16)
    data += bytes([pad_len] * pad_len)
    ciphertext = encryptor.update(data) + encryptor.finalize()
    combined = salt + iv + ciphertext
    return base64.b64encode(combined).decode("ascii")


def decrypt(ciphertext_b64: str, password: str) -> str | None:
    try:
        combined = base64.b64decode(ciphertext_b64)
        salt = combined[:SALT_LENGTH]
        iv = combined[SALT_LENGTH : SALT_LENGTH + IV_LENGTH]
        actual = combined[SALT_LENGTH + IV_LENGTH :]
        key = _derive_key(password, salt)
        cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
        decryptor = cipher.decryptor()
        padded = decryptor.update(actual) + decryptor.finalize()
        pad_len = padded[-1]
        if pad_len < 1 or pad_len > 16:
            return None
        return padded[:-pad_len].decode("utf-8")
    except Exception:
        return None
