from __future__ import annotations

import os
from pathlib import Path

import pytest
import typer
from pytest_mock import MockerFixture

from kleys import modes
from kleys.keyring_ import KeyringUnavailableError


class TestParseEnv:
    def test_simple_key_value(self) -> None:
        assert modes._parse_env("KEY=value") == {"KEY": "value"}

    def test_multi_line(self) -> None:
        content = "A=1\nB=2\nC=3"
        assert modes._parse_env(content) == {"A": "1", "B": "2", "C": "3"}

    def test_skips_comments(self) -> None:
        content = "# comment\nKEY=val\n# another"
        assert modes._parse_env(content) == {"KEY": "val"}

    def test_skips_empty_lines(self) -> None:
        content = "\n\nKEY=val\n\n"
        assert modes._parse_env(content) == {"KEY": "val"}

    def test_skips_lines_without_equals(self) -> None:
        content = "KEY=val\nINVALID\nOTHER=thing"
        assert modes._parse_env(content) == {"KEY": "val", "OTHER": "thing"}

    def test_value_contains_equals(self) -> None:
        content = "URL=postgres://user:pass@host/db?ssl=true"
        assert modes._parse_env(content) == {
            "URL": "postgres://user:pass@host/db?ssl=true"
        }

    def test_strips_whitespace(self) -> None:
        content = "  KEY  =  value  "
        assert modes._parse_env(content) == {"KEY": "value"}

    def test_empty_content(self) -> None:
        assert modes._parse_env("") == {}

    def test_only_comments_and_blank(self) -> None:
        content = "# comment\n\n# another\n"
        assert modes._parse_env(content) == {}


class TestOfferStoreFile:
    def test_user_accepts_plaintext(
        self, mocker: MockerFixture, tmp_path: Path
    ) -> None:
        file = tmp_path / ".env"
        file.write_text("KEY=val\n")
        mocker.patch("typer.prompt", return_value="y")
        kr_store = mocker.patch("kleys.modes.kr.store")
        result = modes._offer_store_file(str(file), "myapp", None, True)
        assert result is True
        kr_store.assert_called_once_with("myapp", "KEY=val\n")

    def test_user_accepts_encrypted(
        self, mocker: MockerFixture, tmp_path: Path
    ) -> None:
        file = tmp_path / ".env"
        file.write_text("KEY=val\n")
        mocker.patch("typer.prompt", return_value="y")
        mocker.patch("kleys.modes.resolve_encrypt_password", return_value="pw")
        mocker.patch(
            "kleys.modes.crypto.encrypt",
            return_value="encrypted-blob",
        )
        kr_store = mocker.patch("kleys.modes.kr.store")
        result = modes._offer_store_file(str(file), "myapp", None, False)
        assert result is True
        kr_store.assert_called_once_with("myapp-encrypted", "encrypted-blob")

    def test_user_declines(self, mocker: MockerFixture, tmp_path: Path) -> None:
        file = tmp_path / ".env"
        file.write_text("K=v\n")
        mocker.patch("typer.prompt", return_value="n")
        kr_store = mocker.patch("kleys.modes.kr.store")
        result = modes._offer_store_file(str(file), "myapp", None, True)
        assert result is False
        kr_store.assert_not_called()

    def test_no_password_available(
        self, mocker: MockerFixture, tmp_path: Path
    ) -> None:
        file = tmp_path / ".env"
        file.write_text("K=v\n")
        mocker.patch("typer.prompt", return_value="y")
        mocker.patch("kleys.modes.resolve_encrypt_password", return_value=None)
        with pytest.raises(SystemExit):
            modes._offer_store_file(str(file), "myapp", None, False)

    def test_abort_on_prompt(
        self, mocker: MockerFixture, tmp_path: Path
    ) -> None:
        import typer as _typer

        file = tmp_path / ".env"
        file.write_text("K=v\n")
        mocker.patch("typer.prompt", side_effect=_typer.Abort)
        kr_store = mocker.patch("kleys.modes.kr.store")
        result = modes._offer_store_file(str(file), "myapp", None, True)
        assert result is False
        kr_store.assert_not_called()

    def test_store_keyring_unavailable_plaintext(
        self, mocker: MockerFixture, tmp_path: Path
    ) -> None:
        file = tmp_path / ".env"
        file.write_text("K=v\n")
        mocker.patch("typer.prompt", return_value="y")
        mocker.patch(
            "kleys.modes.kr.store",
            side_effect=KeyringUnavailableError,
        )
        with pytest.raises(SystemExit):
            modes._offer_store_file(str(file), "myapp", None, True)

    def test_store_keyring_unavailable_encrypted(
        self, mocker: MockerFixture, tmp_path: Path
    ) -> None:
        file = tmp_path / ".env"
        file.write_text("K=v\n")
        mocker.patch("typer.prompt", return_value="y")
        mocker.patch("kleys.modes.resolve_encrypt_password", return_value="pw")
        mocker.patch("kleys.modes.crypto.encrypt", return_value="encrypted")
        mocker.patch(
            "kleys.modes.kr.store",
            side_effect=KeyringUnavailableError,
        )
        with pytest.raises(SystemExit):
            modes._offer_store_file(str(file), "myapp", None, False)


class TestTryLoadFromKeyring:
    def test_encrypted_found_decrypts_and_returns(
        self, mocker: MockerFixture
    ) -> None:
        mocker.patch(
            "kleys.modes.kr.lookup",
            side_effect=lambda s: (
                "encrypted-blob" if s == "myapp-encrypted" else None
            ),
        )
        mocker.patch("kleys.modes.resolve_decrypt_password", return_value="pw")
        mocker.patch(
            "kleys.modes.crypto.decrypt",
            return_value="decrypted-content",
        )
        result = modes._try_load_from_keyring("myapp", None, False)
        assert result == "decrypted-content"

    def test_no_password_exits(self, mocker: MockerFixture) -> None:
        mocker.patch(
            "kleys.modes.kr.lookup",
            return_value="encrypted-blob",
        )
        mocker.patch("kleys.modes.resolve_decrypt_password", return_value=None)
        with pytest.raises(SystemExit):
            modes._try_load_from_keyring("myapp", None, False)

    def test_decrypt_fails_exits(self, mocker: MockerFixture) -> None:
        mocker.patch(
            "kleys.modes.kr.lookup",
            side_effect=lambda s: (
                "encrypted-blob" if s == "myapp-encrypted" else None
            ),
        )
        mocker.patch("kleys.modes.resolve_decrypt_password", return_value="pw")
        mocker.patch("kleys.modes.crypto.decrypt", return_value=None)
        with pytest.raises(SystemExit):
            modes._try_load_from_keyring("myapp", None, False)

    def test_plaintext_found_returns(self, mocker: MockerFixture) -> None:
        mocker.patch(
            "kleys.modes.kr.lookup",
            side_effect=lambda s: (
                None if s == "myapp-encrypted" else "plain-content"
            ),
        )
        result = modes._try_load_from_keyring("myapp", None, False)
        assert result == "plain-content"

    def test_none_when_missing(self, mocker: MockerFixture) -> None:
        mocker.patch("kleys.modes.kr.lookup", return_value=None)
        result = modes._try_load_from_keyring("myapp", None, False)
        assert result is None

    def test_none_when_missing_plaintext_mode(
        self, mocker: MockerFixture
    ) -> None:
        mocker.patch("kleys.modes.kr.lookup", return_value=None)
        result = modes._try_load_from_keyring("myapp", None, True)
        assert result is None


class TestInteractivePromptAndStore:
    def test_user_input_encrypted(self, mocker: MockerFixture) -> None:
        mocker.patch("builtins.input", side_effect=["USER=provided", EOFError])
        mocker.patch("kleys.modes.resolve_encrypt_password", return_value="pw")
        mocker.patch("kleys.modes.crypto.encrypt", return_value="encrypted")
        result = modes._interactive_prompt_and_store("myapp", None, False)
        assert result == "USER=provided"

    def test_user_input_plaintext(self, mocker: MockerFixture) -> None:
        mocker.patch("builtins.input", side_effect=["plain=text", EOFError])
        result = modes._interactive_prompt_and_store("myapp", None, True)
        assert result == "plain=text"

    def test_empty_line_terminates(self, mocker: MockerFixture) -> None:
        mocker.patch("builtins.input", side_effect=["KEY=val", ""])
        mocker.patch("kleys.modes.resolve_encrypt_password", return_value="pw")
        mocker.patch("kleys.modes.crypto.encrypt", return_value="encrypted")
        result = modes._interactive_prompt_and_store("myapp", None, False)
        assert result == "KEY=val"

    def test_empty_input_exits(self, mocker: MockerFixture) -> None:
        mocker.patch("builtins.input", side_effect=EOFError)
        with pytest.raises(SystemExit):
            modes._interactive_prompt_and_store("myapp", None, False)

    def test_no_password_error_exits(self, mocker: MockerFixture) -> None:
        mocker.patch("builtins.input", side_effect=["KEY=val", EOFError])
        mocker.patch("kleys.modes.resolve_encrypt_password", return_value=None)
        with pytest.raises(SystemExit):
            modes._interactive_prompt_and_store("myapp", None, False)

    def test_keyring_unavailable_plaintext_exits(
        self, mocker: MockerFixture
    ) -> None:
        mocker.patch("builtins.input", side_effect=["USER=provided", EOFError])
        mocker.patch(
            "kleys.modes.kr.store",
            side_effect=KeyringUnavailableError,
        )
        with pytest.raises(SystemExit):
            modes._interactive_prompt_and_store("myapp", None, True)

    def test_keyring_unavailable_encrypted_exits(
        self, mocker: MockerFixture
    ) -> None:
        mocker.patch("builtins.input", side_effect=["USER=provided", EOFError])
        mocker.patch("kleys.modes.resolve_encrypt_password", return_value="pw")
        mocker.patch("kleys.modes.crypto.encrypt", return_value="encrypted")
        mocker.patch(
            "kleys.modes.kr.store",
            side_effect=KeyringUnavailableError,
        )
        with pytest.raises(SystemExit):
            modes._interactive_prompt_and_store("myapp", None, False)


class TestExecFile:
    def test_writes_to_file_path_and_runs(
        self, mocker: MockerFixture, tmp_path: Path
    ) -> None:
        secrets_path = tmp_path / ".env"
        mocker.patch("kleys.utils._FILE_PATH", None)
        mocker.patch("os.chmod")
        import subprocess

        content = "CONTENT=val\n"
        result = modes._exec_file(["echo", "hi"], content, str(secrets_path))
        assert result == 0
        assert secrets_path.read_text() == content
        subprocess.run.assert_called_once()
        env_arg = subprocess.run.call_args[1]["env"]
        assert env_arg["SECRETS_FILE"] == str(secrets_path)

    def test_file_not_found_error(
        self, mocker: MockerFixture, tmp_path: Path
    ) -> None:
        secrets_path = tmp_path / ".env"
        mocker.patch("kleys.utils._FILE_PATH", None)
        mocker.patch("os.chmod")
        import subprocess

        mocker.patch.object(subprocess, "run", side_effect=FileNotFoundError())
        content = "CONTENT=val\n"
        result = modes._exec_file(["nonexistent"], content, str(secrets_path))
        assert result == 127


class TestExecSource:
    def test_sets_env_and_runs(self) -> None:
        import subprocess

        subprocess.run.reset_mock()
        result = modes._exec_source(
            ["printenv"], "DB_URL=postgres://localhost/db\n"
        )
        assert result == 0
        subprocess.run.assert_called_once()
        env_arg = subprocess.run.call_args[1]["env"]
        assert env_arg["DB_URL"] == "postgres://localhost/db"

    def test_file_not_found_error(self, mocker: MockerFixture) -> None:
        import subprocess

        mocker.patch.object(subprocess, "run", side_effect=FileNotFoundError())
        result = modes._exec_source(["nonexistent"], "CONTENT=val\n")
        assert result == 127


class TestExecFD:
    def test_creates_pipe_and_runs(self, mocker: MockerFixture) -> None:
        mocker.patch("os.pipe", return_value=(10, 11))
        mocker.patch("os.write", side_effect=lambda fd, data: len(data))
        mocker.patch("os.close")
        import subprocess

        subprocess.run.reset_mock()
        result = modes._exec_fd(
            ["tool", "--file", "@SECRETS@"], "SECRET=data\n"
        )
        assert result == 0
        os.write.assert_called_once_with(11, b"SECRET=data\n")
        modified_args = subprocess.run.call_args[0][0]
        assert modified_args == ["tool", "--file", "/dev/fd/10"]
        env_arg = subprocess.run.call_args[1]["env"]
        assert env_arg["SECRETS_FILE"] == "/dev/fd/10"

    def test_no_at_secrets(self, mocker: MockerFixture) -> None:
        mocker.patch("os.pipe", return_value=(10, 11))
        mocker.patch("os.write", side_effect=lambda fd, data: len(data))
        mocker.patch("os.close")
        import subprocess

        subprocess.run.reset_mock()
        result = modes._exec_fd(["tool", "arg"], "DATA=val\n")
        assert result == 0
        modified_args = subprocess.run.call_args[0][0]
        assert modified_args == ["tool", "arg"]

    def test_multiple_at_secrets_tokens(self, mocker: MockerFixture) -> None:
        mocker.patch("os.pipe", return_value=(10, 11))
        mocker.patch("os.write", side_effect=lambda fd, data: len(data))
        mocker.patch("os.close")
        import subprocess

        subprocess.run.reset_mock()
        result = modes._exec_fd(
            ["tool", "@SECRETS@", "--other", "@SECRETS@"], "D=A\n"
        )
        assert result == 0
        modified_args = subprocess.run.call_args[0][0]
        assert modified_args == ["tool", "/dev/fd/10", "--other", "/dev/fd/10"]


class TestDispatch:
    def test_empty_command_exits(self, mocker: MockerFixture) -> None:
        mocker.patch("kleys.utils.setup_cleanup")
        with pytest.raises(SystemExit) as exc:
            modes.dispatch(
                command=[],
                file=".env",
                app_name="testapp",
                source_mode=False,
                password=None,
                plaintext_mode=False,
            )
        assert exc.value.code == 1

    def test_file_mode(self, mocker: MockerFixture) -> None:
        mocker.patch("kleys.modes.kr.lookup", return_value=None)
        mocker.patch("typer.prompt", return_value="n")
        mocker.patch("typer.confirm", return_value=True)
        mocker.patch("typer.echo")
        mocker.patch("builtins.input", side_effect=["KEY=val", EOFError])
        mocker.patch("kleys.modes.resolve_encrypt_password", return_value="pw")
        mocker.patch("kleys.modes.crypto.encrypt", return_value="encrypted")
        mocker.patch("tempfile.mkstemp", return_value=(3, "/tmp/test.env"))
        mocker.patch("builtins.open", mocker.mock_open())
        mocker.patch("os.chmod")
        mocker.patch("os.close")
        mocker.patch("kleys.utils.setup_cleanup")
        import subprocess

        subprocess.run.reset_mock()
        with pytest.raises(SystemExit) as exc:
            modes.dispatch(
                command=["echo", "hello"],
                file=".env",
                app_name="testapp",
                source_mode=False,
                password=None,
                plaintext_mode=False,
            )
        assert exc.value.code == 0
        subprocess.run.assert_called_once()

    def test_source_mode(self, mocker: MockerFixture) -> None:
        mocker.patch("kleys.modes.kr.lookup", return_value=None)
        mocker.patch("typer.prompt", return_value="n")
        mocker.patch("typer.echo")
        mocker.patch("builtins.input", side_effect=["DB=prod", EOFError])
        mocker.patch("kleys.modes.resolve_encrypt_password", return_value="pw")
        mocker.patch("kleys.modes.crypto.encrypt", return_value="encrypted")
        mocker.patch("kleys.utils.setup_cleanup")
        import subprocess

        subprocess.run.reset_mock()
        with pytest.raises(SystemExit) as exc:
            modes.dispatch(
                command=["ansible", "playbook.yml"],
                file=".env",
                app_name="testapp",
                source_mode=True,
                password=None,
                plaintext_mode=False,
            )
        assert exc.value.code == 0
        env_arg = subprocess.run.call_args[1]["env"]
        assert env_arg["DB"] == "prod"

    def test_fd_mode_unix(self, mocker: MockerFixture) -> None:
        mocker.patch("kleys.modes.kr.lookup", return_value=None)
        mocker.patch("kleys.modes.resolve_encrypt_password", return_value="pw")
        mocker.patch("kleys.modes.crypto.encrypt", return_value="encrypted")
        mocker.patch("os.pipe", return_value=(10, 11))
        mocker.patch("os.write", side_effect=lambda fd, data: len(data))
        mocker.patch("os.close")
        mocker.patch("builtins.input", side_effect=["K=V", EOFError])
        mocker.patch("sys.platform", "linux")
        mocker.patch("kleys.utils.setup_cleanup")
        import subprocess

        subprocess.run.reset_mock()
        with pytest.raises(SystemExit) as exc:
            modes.dispatch(
                command=["act", "--secret-file", "@SECRETS@"],
                file=".env",
                app_name="testapp",
                source_mode=False,
                password=None,
                plaintext_mode=False,
            )
        assert exc.value.code == 0
        modified_args = subprocess.run.call_args[0][0]
        assert modified_args == ["act", "--secret-file", "/dev/fd/10"]

    def test_fd_mode_windows_error(self, mocker: MockerFixture) -> None:
        mocker.patch("kleys.modes.kr.lookup", return_value=None)
        mocker.patch("kleys.modes.resolve_encrypt_password", return_value="pw")
        mocker.patch("kleys.modes.crypto.encrypt", return_value="encrypted")
        mocker.patch("builtins.input", side_effect=["K=V", EOFError])
        mocker.patch("sys.platform", "win32")
        mocker.patch("kleys.utils.setup_cleanup")
        with pytest.raises(SystemExit) as exc:
            modes.dispatch(
                command=["tool", "@SECRETS@"],
                file=".env",
                app_name="testapp",
                source_mode=False,
                password=None,
                plaintext_mode=False,
            )
        assert exc.value.code == 1

    def test_local_file_store_accepted(
        self, mocker: MockerFixture, tmp_path: Path
    ) -> None:
        file = tmp_path / ".env"
        file.write_text("LOCAL=stored\n")
        mocker.patch("typer.prompt", return_value="y")
        mocker.patch("kleys.modes.resolve_encrypt_password", return_value="pw")
        mocker.patch("kleys.modes.crypto.encrypt", return_value="encrypted")
        mocker.patch("kleys.modes.kr.store")
        mocker.patch("kleys.modes.kr.lookup", return_value=None)
        mocker.patch("builtins.input", side_effect=["KEY=val", EOFError])
        mocker.patch("tempfile.mkstemp", return_value=(3, "/tmp/test.env"))
        mocker.patch("builtins.open", mocker.mock_open())
        mocker.patch("os.chmod")
        mocker.patch("os.close")
        mocker.patch("kleys.utils.setup_cleanup")
        import subprocess

        subprocess.run.reset_mock()
        with pytest.raises(SystemExit):
            modes.dispatch(
                command=["run", "me"],
                file=str(file),
                app_name="testapp",
                source_mode=False,
                password=None,
                plaintext_mode=False,
            )
        assert not file.exists()
        subprocess.run.assert_called_once()

    def test_local_file_decline_file_mode(
        self, mocker: MockerFixture, tmp_path: Path
    ) -> None:
        file = tmp_path / ".env"
        file.write_text("LOCAL=used\n")
        mocker.patch("typer.prompt", return_value="n")
        mocker.patch("typer.confirm", return_value=True)
        mocker.patch("kleys.modes.resolve_encrypt_password", return_value="pw")
        mocker.patch("kleys.modes.crypto.encrypt", return_value="encrypted")
        mocker.patch("kleys.modes.kr.store")
        mocker.patch("kleys.modes.kr.lookup", return_value=None)
        mocker.patch("builtins.input", side_effect=["KEY=pasted", ""])
        mocker.patch("builtins.open", mocker.mock_open())
        mocker.patch("os.chmod")
        mocker.patch("kleys.utils.setup_cleanup")
        import subprocess

        subprocess.run.reset_mock()
        with pytest.raises(SystemExit):
            modes.dispatch(
                command=["run", "me"],
                file=str(file),
                app_name="testapp",
                source_mode=False,
                password=None,
                plaintext_mode=False,
            )
        env_arg = subprocess.run.call_args[1]["env"]
        assert env_arg["SECRETS_FILE"] == str(file.absolute())

    def test_local_file_decline_source_mode(
        self, mocker: MockerFixture, tmp_path: Path
    ) -> None:
        file = tmp_path / ".env"
        file.write_text("LOCAL=env_var\n")
        mocker.patch("typer.prompt", return_value="n")
        mocker.patch("kleys.modes.resolve_encrypt_password", return_value="pw")
        mocker.patch("kleys.modes.crypto.encrypt", return_value="encrypted")
        mocker.patch("kleys.modes.kr.store")
        mocker.patch("kleys.modes.kr.lookup", return_value=None)
        mocker.patch("builtins.input", side_effect=["KEY=pasted_value", ""])
        mocker.patch("kleys.utils.setup_cleanup")
        import subprocess

        subprocess.run.reset_mock()
        with pytest.raises(SystemExit):
            modes.dispatch(
                command=["tool"],
                file=str(file),
                app_name="testapp",
                source_mode=True,
                password=None,
                plaintext_mode=False,
            )
        env_arg = subprocess.run.call_args[1]["env"]
        assert env_arg["KEY"] == "pasted_value"

    def test_local_file_decline_file_mode_not_found(
        self, mocker: MockerFixture, tmp_path: Path
    ) -> None:
        file = tmp_path / ".env"
        file.write_text("LOCAL=used\n")
        mocker.patch("typer.prompt", return_value="n")
        mocker.patch("typer.confirm", return_value=True)
        mocker.patch("kleys.modes.resolve_encrypt_password", return_value="pw")
        mocker.patch("kleys.modes.crypto.encrypt", return_value="encrypted")
        mocker.patch("kleys.modes.kr.store")
        mocker.patch("kleys.modes.kr.lookup", return_value=None)
        mocker.patch("builtins.input", side_effect=["KEY=val", ""])
        mocker.patch("builtins.open", mocker.mock_open())
        mocker.patch("os.chmod")
        mocker.patch("kleys.utils.setup_cleanup")
        import subprocess

        subprocess.run.reset_mock()
        mocker.patch.object(subprocess, "run", side_effect=FileNotFoundError())
        with pytest.raises(SystemExit) as exc:
            modes.dispatch(
                command=["nonexistent"],
                file=str(file),
                app_name="testapp",
                source_mode=False,
                password=None,
                plaintext_mode=False,
            )
        assert exc.value.code == 127

    def test_local_file_decline_source_mode_not_found(
        self, mocker: MockerFixture, tmp_path: Path
    ) -> None:
        file = tmp_path / ".env"
        file.write_text("LOCAL=env_var\n")
        mocker.patch("typer.prompt", return_value="n")
        mocker.patch("kleys.modes.resolve_encrypt_password", return_value="pw")
        mocker.patch("kleys.modes.crypto.encrypt", return_value="encrypted")
        mocker.patch("kleys.modes.kr.store")
        mocker.patch("kleys.modes.kr.lookup", return_value=None)
        mocker.patch("builtins.input", side_effect=["KEY=val", ""])
        mocker.patch("kleys.utils.setup_cleanup")
        import subprocess

        subprocess.run.reset_mock()
        mocker.patch.object(subprocess, "run", side_effect=FileNotFoundError())
        with pytest.raises(SystemExit) as exc:
            modes.dispatch(
                command=["nonexistent"],
                file=str(file),
                app_name="testapp",
                source_mode=True,
                password=None,
                plaintext_mode=False,
            )
        assert exc.value.code == 127

    def test_local_file_key_exists_file_mode(
        self, mocker: MockerFixture, tmp_path: Path
    ) -> None:
        file = tmp_path / ".env"
        file.write_text("LOCAL=from_dotenv\n")
        mocker.patch(
            "kleys.modes.kr.lookup",
            side_effect=lambda s: (
                "encrypted-blob" if s == "testapp-encrypted" else None
            ),
        )
        mocker.patch("kleys.modes.resolve_decrypt_password", return_value="pw")
        mocker.patch(
            "kleys.modes.crypto.decrypt", return_value="KEY=from_keyring"
        )
        mocker.patch("typer.confirm", return_value=True)
        mocker.patch("typer.echo")
        mocker.patch("builtins.open", mocker.mock_open())
        mocker.patch("os.chmod")
        mocker.patch("kleys.utils.setup_cleanup")
        import subprocess

        subprocess.run.reset_mock()
        with pytest.raises(SystemExit):
            modes.dispatch(
                command=["run", "me"],
                file=str(file),
                app_name="testapp",
                source_mode=False,
                password=None,
                plaintext_mode=False,
            )
        env_arg = subprocess.run.call_args[1]["env"]
        assert env_arg["SECRETS_FILE"] == str(file.absolute())

    def test_local_file_key_exists_source_mode(
        self, mocker: MockerFixture, tmp_path: Path
    ) -> None:
        file = tmp_path / ".env"
        file.write_text("LOCAL=from_dotenv\n")
        mocker.patch(
            "kleys.modes.kr.lookup",
            side_effect=lambda s: (
                "encrypted-blob" if s == "testapp-encrypted" else None
            ),
        )
        mocker.patch("kleys.modes.resolve_decrypt_password", return_value="pw")
        mocker.patch(
            "kleys.modes.crypto.decrypt", return_value="KEY=from_keyring"
        )
        mocker.patch("kleys.utils.setup_cleanup")
        import subprocess

        subprocess.run.reset_mock()
        with pytest.raises(SystemExit):
            modes.dispatch(
                command=["tool"],
                file=str(file),
                app_name="testapp",
                source_mode=True,
                password=None,
                plaintext_mode=False,
            )
        env_arg = subprocess.run.call_args[1]["env"]
        assert env_arg["KEY"] == "from_keyring"
        assert "LOCAL" not in env_arg

    def test_local_file_decline_overwrite_cancelled(
        self, mocker: MockerFixture, tmp_path: Path
    ) -> None:
        file = tmp_path / ".env"
        file.write_text("SECRET=old\n")
        mocker.patch("typer.prompt", return_value="n")
        mocker.patch("typer.confirm", return_value=False)
        mocker.patch("kleys.utils.setup_cleanup")
        with pytest.raises(SystemExit) as exc:
            modes.dispatch(
                command=["tool"],
                file=str(file),
                app_name="testapp",
                source_mode=False,
                password=None,
                plaintext_mode=False,
            )
        assert exc.value.code == 1

    def test_local_file_decline_overwrite_abort(
        self, mocker: MockerFixture, tmp_path: Path
    ) -> None:
        file = tmp_path / ".env"
        file.write_text("SECRET=old\n")
        mocker.patch("typer.prompt", return_value="n")
        mocker.patch("typer.confirm", side_effect=typer.Abort)
        mocker.patch("kleys.utils.setup_cleanup")
        with pytest.raises(SystemExit) as exc:
            modes.dispatch(
                command=["tool"],
                file=str(file),
                app_name="testapp",
                source_mode=False,
                password=None,
                plaintext_mode=False,
            )
        assert exc.value.code == 1
