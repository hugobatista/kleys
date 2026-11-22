from __future__ import annotations

import os
import sys

import pytest

from kleys import utils


class TestParseEnv:
    def test_simple_key_value(self) -> None:
        assert utils.parse_env("KEY=value") == {"KEY": "value"}

    def test_multi_line(self) -> None:
        content = "A=1\nB=2\nC=3"
        assert utils.parse_env(content) == {"A": "1", "B": "2", "C": "3"}

    def test_skips_comments(self) -> None:
        content = "# comment\nKEY=val\n# another"
        assert utils.parse_env(content) == {"KEY": "val"}

    def test_skips_empty_lines(self) -> None:
        content = "\n\nKEY=val\n\n"
        assert utils.parse_env(content) == {"KEY": "val"}

    def test_skips_lines_without_equals(self) -> None:
        content = "KEY=val\nINVALID\nOTHER=thing"
        assert utils.parse_env(content) == {"KEY": "val", "OTHER": "thing"}

    def test_value_contains_equals(self) -> None:
        content = "URL=postgres://user:pass@host/db?ssl=true"
        assert utils.parse_env(content) == {
            "URL": "postgres://user:pass@host/db?ssl=true"
        }

    def test_strips_whitespace(self) -> None:
        content = "  KEY  =  value  "
        assert utils.parse_env(content) == {"KEY": "value"}

    def test_duplicate_keys_last_wins(self) -> None:
        content = "KEY=first\nKEY=second"
        assert utils.parse_env(content) == {"KEY": "second"}

    def test_empty_content(self) -> None:
        assert utils.parse_env("") == {}

    def test_only_comments_and_blank(self) -> None:
        content = "# comment\n\n# another\n"
        assert utils.parse_env(content) == {}


class TestCreateTempEnv:
    def test_creates_file_with_content(self) -> None:
        path = utils.create_temp_env("KEY=value\n")
        assert os.path.exists(path)
        with open(path) as f:
            assert f.read() == "KEY=value\n"

    @pytest.mark.skipif(
        sys.platform == "win32",
        reason="chmod semantics differ on Windows",
    )
    def test_sets_600_permissions(self) -> None:
        path = utils.create_temp_env("SECRET=x\n")
        mode = os.stat(path).st_mode & 0o777
        assert mode == 0o600

    def test_skips_chmod_on_windows(self, mocker) -> None:
        mocker.patch("sys.platform", "win32")
        chmod = mocker.patch("os.chmod")
        path = utils.create_temp_env("SECRET=x\n")
        assert os.path.exists(path)
        chmod.assert_not_called()

    def test_calls_chmod_on_unix(self, mocker) -> None:
        mocker.patch("sys.platform", "linux")
        chmod = mocker.patch("os.chmod")
        mocker.patch("os.close")
        path = utils.create_temp_env("SECRET=x\n")
        chmod.assert_called_once_with(path, 0o600)

    def test_creates_tracked_path(self) -> None:
        utils.reset_cleanup_state()
        path = utils.create_temp_env("DATA=xyz\n")
        assert utils.get_temp_path() == path


class TestCleanup:
    def test_removes_temp_file(self) -> None:
        utils.reset_cleanup_state()
        path = utils.create_temp_env("clean=me\n")
        assert os.path.exists(path)
        utils._cleanup()
        assert not os.path.exists(path)
        assert utils.get_temp_path() is None

    def test_idempotent_when_no_file(self) -> None:
        utils.reset_cleanup_state()
        utils._cleanup()
        assert utils.get_temp_path() is None

    def test_handles_missing_file_gracefully(self) -> None:
        utils.reset_cleanup_state()
        path = utils.create_temp_env("gone=soon\n")
        os.remove(path)
        utils._cleanup()
        assert utils.get_temp_path() is None

    def test_handles_deleted_between_checks(self, mocker) -> None:
        utils.reset_cleanup_state()
        path = utils.create_temp_env("race=condition\n")
        original_exists = os.path.exists

        def exists_second_call(p):
            if p == path:
                return False
            return original_exists(p)

        mocker.patch("os.path.exists", side_effect=exists_second_call)
        utils._cleanup()

    def test_handles_oserror_on_remove(self, mocker) -> None:
        utils.reset_cleanup_state()
        utils.create_temp_env("error=test\n")
        mocker.patch("os.remove", side_effect=OSError("permission denied"))
        utils._cleanup()
        assert utils.get_temp_path() is None


class TestSignalHandler:
    def test_exits_with_128_plus_signum(self) -> None:
        utils.reset_cleanup_state()
        path = utils.create_temp_env("signal=test\n")
        assert os.path.exists(path)
        with pytest.raises(SystemExit) as exc:
            utils._signal_handler(2, None)
        assert exc.value.code == 130
        assert not os.path.exists(path)

    def test_cleanup_before_exit(self) -> None:
        utils.reset_cleanup_state()
        path = utils.create_temp_env("before=exit\n")
        with pytest.raises(SystemExit):
            utils._signal_handler(15, None)
        assert not os.path.exists(path)


class TestSetupCleanup:
    def test_registers_atexit(self, mocker) -> None:
        atexit_register = mocker.patch("atexit.register")
        signal_signal = mocker.patch("signal.signal")
        utils.setup_cleanup()
        atexit_register.assert_called_once_with(utils._cleanup)
        if sys.platform == "win32":
            signal_signal.assert_called_once_with(2, utils._signal_handler)
        else:
            signal_signal.assert_any_call(15, utils._signal_handler)

    def test_registers_signal_sigint(self, mocker) -> None:
        mocker.patch("atexit.register")
        signal_signal = mocker.patch("signal.signal")
        utils.setup_cleanup()
        signal_signal.assert_any_call(2, utils._signal_handler)

    def test_registers_signal_sigterm_on_unix(self, mocker) -> None:
        mocker.patch("atexit.register")
        mocker.patch("sys.platform", "linux")
        signal_signal = mocker.patch("signal.signal")
        utils.setup_cleanup()
        signal_signal.assert_any_call(15, utils._signal_handler)


class TestResetCleanupState:
    def test_clears_path(self) -> None:
        utils.create_temp_env("data\n")
        assert utils.get_temp_path() is not None
        utils.reset_cleanup_state()
        assert utils.get_temp_path() is None
