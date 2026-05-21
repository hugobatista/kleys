from __future__ import annotations

import typer
from pytest_mock import MockerFixture

from kleys import console


class TestInfo:
    def test_calls_secho_with_cyan(self, mocker: MockerFixture) -> None:
        secho = mocker.patch("typer.secho")
        console.info("hello")
        secho.assert_called_once_with("hello", fg=typer.colors.CYAN)


class TestSuccess:
    def test_calls_secho_with_green(self, mocker: MockerFixture) -> None:
        secho = mocker.patch("typer.secho")
        console.success("done")
        secho.assert_called_once_with("done", fg=typer.colors.GREEN)


class TestWarn:
    def test_calls_secho_with_yellow(self, mocker: MockerFixture) -> None:
        secho = mocker.patch("typer.secho")
        console.warn("careful")
        secho.assert_called_once_with("careful", fg=typer.colors.YELLOW)


class TestError:
    def test_calls_secho_with_red_and_err(self, mocker: MockerFixture) -> None:
        secho = mocker.patch("typer.secho")
        console.error("fail")
        secho.assert_called_once_with("fail", fg=typer.colors.RED, err=True)


class TestCmd:
    def test_secho_with_cyan_and_bold(self, mocker: MockerFixture) -> None:
        secho = mocker.patch("typer.secho")
        console.cmd("run")
        secho.assert_called_once_with("run", fg=typer.colors.CYAN, bold=True)
