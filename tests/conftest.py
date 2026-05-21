from __future__ import annotations

import sys
from collections.abc import Generator
from pathlib import Path

import pytest
from pytest_mock import MockerFixture


@pytest.fixture(autouse=True)
def reset_utils_state() -> Generator[None, None, None]:
    from kleys import utils

    utils.reset_cleanup_state()
    yield


@pytest.fixture(autouse=True)
def mock_keyring(mocker: MockerFixture) -> None:
    mocker.patch("keyring.set_password")
    mocker.patch("keyring.get_password", return_value=None)
    mocker.patch("keyring.delete_password", return_value=None)
    mocker.patch("keyring.errors.KeyringError", Exception)
    mocker.patch("keyring.errors.PasswordDeleteError", Exception)


@pytest.fixture(autouse=True)
def mock_atexit(mocker: MockerFixture) -> None:
    mocker.patch("atexit.register")


@pytest.fixture(autouse=True)
def mock_signal(mocker: MockerFixture) -> None:
    mocker.patch("signal.signal")


@pytest.fixture(autouse=True)
def mock_subprocess_run(mocker: MockerFixture) -> None:
    m = mocker.patch("subprocess.run")
    proc = mocker.MagicMock()
    proc.returncode = 0
    m.return_value = proc


@pytest.fixture
def in_temp_dir(tmp_path: Path) -> Path:
    try:
        (tmp_path / ".env").write_text("ORIGINAL_KEY=original_value\n")
    except Exception:
        pass
    yield tmp_path


@pytest.fixture
def mock_is_tty(mocker: MockerFixture) -> None:
    mocker.patch.object(sys.stdin, "isatty", return_value=True)


@pytest.fixture
def mock_non_tty(mocker: MockerFixture) -> None:
    mocker.patch.object(sys.stdin, "isatty", return_value=False)
