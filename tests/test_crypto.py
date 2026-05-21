from __future__ import annotations

from kleys import crypto


class TestEncryptDecrypt:
    def test_round_trip(self) -> None:
        plaintext = (
            "DATABASE_URL=postgres://user:pass@localhost/db\n"
            "API_KEY=secret123\n"
        )
        password = "hunter2"
        encrypted = crypto.encrypt(plaintext, password)
        assert encrypted != plaintext
        decrypted = crypto.decrypt(encrypted, password)
        assert decrypted == plaintext

    def test_wrong_password_returns_none(self) -> None:
        encrypted = crypto.encrypt("SECRET=value", "correct")
        result = crypto.decrypt(encrypted, "wrong")
        assert result is None

    def test_empty_plaintext(self) -> None:
        encrypted = crypto.encrypt("", "pw")
        decrypted = crypto.decrypt(encrypted, "pw")
        assert decrypted == ""

    def test_empty_password(self) -> None:
        encrypted = crypto.encrypt("K=v", "")
        decrypted = crypto.decrypt(encrypted, "")
        assert decrypted == "K=v"

    def test_large_payload(self) -> None:
        plaintext = f"LARGE_KEY={'x' * 100_000}\n"
        encrypted = crypto.encrypt(plaintext, "p4ss")
        decrypted = crypto.decrypt(encrypted, "p4ss")
        assert decrypted == plaintext

    def test_unicode_content(self) -> None:
        plaintext = "\u00dcBER_SECRET=\u00fcber_value\nMONEY=\u20ac100\n"
        encrypted = crypto.encrypt(plaintext, "p\u00e4ssw\u00f6rd")
        decrypted = crypto.decrypt(encrypted, "p\u00e4ssw\u00f6rd")
        assert decrypted == plaintext

    def test_multiple_encryptions_different(self) -> None:
        e1 = crypto.encrypt("K=v", "pw")
        e2 = crypto.encrypt("K=v", "pw")
        assert e1 != e2


class TestDecryptErrors:
    def test_invalid_base64_returns_none(self) -> None:
        assert crypto.decrypt("not-base64!!!", "pw") is None

    def test_truncated_data_returns_none(self) -> None:
        encrypted = crypto.encrypt("K=v", "pw")
        truncated = encrypted[:-10]
        assert crypto.decrypt(truncated, "pw") is None

    def test_garbled_ciphertext_returns_none(self) -> None:
        import base64

        garbled = base64.b64encode(
            b"\x00" * 16 + b"\x01" * 16 + b"\x02" * 16
        ).decode("ascii")
        assert crypto.decrypt(garbled, "pw") is None
