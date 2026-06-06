from __future__ import annotations

import os

import pytest
import typer
from pytest_mock import MockerFixture

from kleys.password import (
    resolve_decrypt_password,
    resolve_encrypt_password,
)


class TestResolveEncryptPassword:
    def test_explicit_password(self) -> None:
        result = resolve_encrypt_password("explicit-pw")
        assert result == "explicit-pw"

    def test_env_var(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("KLEYS_PASSWORD", "env-password")
        result = resolve_encrypt_password(None)
        assert result == "env-password"

    def test_env_var_overrides_prompt(self, mocker: MockerFixture) -> None:
        mocker.patch.object(os, "environ", {"KLEYS_PASSWORD": "env-val"})
        prompt = mocker.patch("typer.prompt")
        result = resolve_encrypt_password(None)
        assert result == "env-val"
        prompt.assert_not_called()

    def test_prompt_with_confirm(self, mocker: MockerFixture) -> None:
        mocker.patch("sys.stdin.isatty", return_value=True)
        mocker.patch("typer.prompt", side_effect=["my-password", "my-password"])
        result = resolve_encrypt_password(None)
        assert result == "my-password"

    def test_prompt_empty_password_retries(self, mocker: MockerFixture) -> None:
        mocker.patch("sys.stdin.isatty", return_value=True)
        mocker.patch("typer.prompt", side_effect=["", "valid_pw", "valid_pw"])
        secho = mocker.patch("typer.secho")
        result = resolve_encrypt_password(None)
        assert result == "valid_pw"
        secho.assert_any_call(
            "Error: Password cannot be empty.",
            fg=typer.colors.RED,
            err=True,
        )

    def test_prompt_mismatch_retries(self, mocker: MockerFixture) -> None:
        mocker.patch("sys.stdin.isatty", return_value=True)
        mocker.patch(
            "typer.prompt",
            side_effect=["password1", "password2", "good", "good"],
        )
        secho = mocker.patch("typer.secho")
        result = resolve_encrypt_password(None)
        assert result == "good"
        secho.assert_any_call(
            "Error: Passwords do not match.",
            fg=typer.colors.RED,
            err=True,
        )

    def test_non_tty_returns_none(self, mocker: MockerFixture) -> None:
        mocker.patch("sys.stdin.isatty", return_value=False)
        result = resolve_encrypt_password(None)
        assert result is None

    def test_explicit_takes_priority_over_env(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("KLEYS_PASSWORD", "env-pw")
        result = resolve_encrypt_password("explicit-pw")
        assert result == "explicit-pw"

    def test_explicit_takes_priority_over_prompt(
        self, mocker: MockerFixture
    ) -> None:
        mocker.patch("sys.stdin.isatty", return_value=True)
        prompt = mocker.patch("typer.prompt")
        result = resolve_encrypt_password("explicit-pw")
        assert result == "explicit-pw"
        prompt.assert_not_called()


class TestResolveDecryptPassword:
    def test_explicit_password(self) -> None:
        result = resolve_decrypt_password("explicit-pw")
        assert result == "explicit-pw"

    def test_env_var(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("KLEYS_PASSWORD", "env-password")
        result = resolve_decrypt_password(None)
        assert result == "env-password"

    def test_prompt(self, mocker: MockerFixture) -> None:
        mocker.patch("sys.stdin.isatty", return_value=True)
        mocker.patch("typer.prompt", return_value="terminal-pw")
        result = resolve_decrypt_password(None)
        assert result == "terminal-pw"

    def test_prompt_empty_returns_none(self, mocker: MockerFixture) -> None:
        mocker.patch("sys.stdin.isatty", return_value=True)
        mocker.patch("typer.prompt", return_value="")
        result = resolve_decrypt_password(None)
        assert result is None

    def test_non_tty_returns_none(self, mocker: MockerFixture) -> None:
        mocker.patch("sys.stdin.isatty", return_value=False)
        result = resolve_decrypt_password(None)
        assert result is None

    def test_no_confirmation_prompt(self, mocker: MockerFixture) -> None:
        mocker.patch("sys.stdin.isatty", return_value=True)
        mocker.patch("typer.prompt", return_value="my-pw")
        echo = mocker.patch("typer.echo")
        resolve_decrypt_password(None)
        echo.assert_called_once_with("")
