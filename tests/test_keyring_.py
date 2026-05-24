from __future__ import annotations

import keyring
import pytest
from pytest_mock import MockerFixture

from kleys import keyring_ as kr


class TestKeyringInstallHint:
    def test_non_linux_hint(self, mocker: MockerFixture) -> None:
        mocker.patch.object(kr, "sys", spec=["platform"])
        kr.sys.platform = "darwin"
        hint = kr.keyring_install_hint()
        assert "pip install keyrings.alt" in hint
        assert "apt install" not in hint

    def test_linux_hint_includes_apt(self, mocker: MockerFixture) -> None:
        mocker.patch.object(kr, "sys", spec=["platform"])
        kr.sys.platform = "linux"
        hint = kr.keyring_install_hint()
        assert "apt install python3-secretstorage" in hint
        assert "Debian/Ubuntu" in hint


class TestStore:
    def test_stores_with_fixed_user(self, mocker: MockerFixture) -> None:
        kr.store("myapp", "secret-content")
        keyring.set_password.assert_called_once_with(
            "myapp", "__secrets__", "secret-content"
        )

    def test_raises_keyring_unavailable_on_error(
        self, mocker: MockerFixture
    ) -> None:
        keyring.set_password.side_effect = keyring.errors.KeyringError("fail")
        with pytest.raises(kr.KeyringUnavailableError):
            kr.store("myapp", "secret")


class TestLookup:
    def test_returns_value_when_found(self, mocker: MockerFixture) -> None:
        keyring.get_password.return_value = "found-secret"
        result = kr.lookup("myapp")
        assert result == "found-secret"
        keyring.get_password.assert_called_once_with("myapp", "__secrets__")

    def test_returns_none_when_missing(self) -> None:
        keyring.get_password.return_value = None
        result = kr.lookup("myapp")
        assert result is None

    def test_returns_none_on_keyring_error(self, mocker: MockerFixture) -> None:
        keyring.get_password.side_effect = keyring.errors.KeyringError("fail")
        result = kr.lookup("myapp")
        assert result is None


class TestDelete:
    def test_returns_true_when_deleted(self, mocker: MockerFixture) -> None:
        keyring.delete_password.return_value = True
        result = kr.delete("myapp")
        assert result is True
        keyring.delete_password.assert_called_once_with("myapp", "__secrets__")

    def test_returns_false_on_delete_error(self, mocker: MockerFixture) -> None:
        keyring.delete_password.side_effect = (
            keyring.errors.PasswordDeleteError("fail")
        )
        result = kr.delete("myapp")
        assert result is False
