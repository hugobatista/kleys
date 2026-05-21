from __future__ import annotations

import sys

import pytest
from pytest_mock import MockerFixture

from kleys import cli


class TestParseOptions:
    def test_no_args_defaults(self) -> None:
        opts, cmd = cli._parse_options([])
        assert opts["file"] == ".env"
        assert opts["app_name"] is None
        assert opts["source_mode"] is False
        assert opts["password"] is None
        assert opts["plaintext_mode"] is False
        assert cmd == []

    def test_help_exits(self) -> None:
        with pytest.raises(SystemExit):
            cli._parse_options(["--help"])

    def test_help_h_exits(self) -> None:
        with pytest.raises(SystemExit):
            cli._parse_options(["-h"])

    def test_file_option(self) -> None:
        opts, cmd = cli._parse_options(["--file", "custom.env", "run", "test"])
        assert opts["file"] == "custom.env"
        assert cmd == ["run", "test"]

    def test_file_short(self) -> None:
        opts, cmd = cli._parse_options(["-f", "custom.env", "run"])
        assert opts["file"] == "custom.env"
        assert cmd == ["run"]

    def test_app_option(self) -> None:
        opts, cmd = cli._parse_options(["--app", "myapp", "run", "test"])
        assert opts["app_name"] == "myapp"
        assert cmd == ["run", "test"]

    def test_app_short(self) -> None:
        opts, cmd = cli._parse_options(["-a", "myapp", "run"])
        assert opts["app_name"] == "myapp"
        assert cmd == ["run"]

    def test_source_flag(self) -> None:
        opts, cmd = cli._parse_options(["--source", "run"])
        assert opts["source_mode"] is True
        assert cmd == ["run"]

    def test_source_short(self) -> None:
        opts, cmd = cli._parse_options(["-s", "run"])
        assert opts["source_mode"] is True
        assert cmd == ["run"]

    def test_password_option(self) -> None:
        opts, cmd = cli._parse_options(["--password", "hunter2", "run"])
        assert opts["password"] == "hunter2"
        assert cmd == ["run"]

    def test_password_missing_value(self) -> None:
        with pytest.raises(SystemExit):
            cli._parse_options(["--password"])

    def test_password_eats_double_dash(self) -> None:
        opts, cmd = cli._parse_options(["--password", "--", "run"])
        assert opts["password"] == "--"
        assert cmd == ["run"]

    def test_plaintext_flag(self) -> None:
        opts, cmd = cli._parse_options(["--plaintext", "run"])
        assert opts["plaintext_mode"] is True
        assert cmd == ["run"]

    def test_all_options(self) -> None:
        opts, cmd = cli._parse_options(
            [
                "--file",
                "secrets.env",
                "--app",
                "myapp",
                "--source",
                "--password",
                "p4ss",
                "--plaintext",
                "command",
                "--arg",
                "value",
            ],
        )
        assert opts["file"] == "secrets.env"
        assert opts["app_name"] == "myapp"
        assert opts["source_mode"] is True
        assert opts["password"] == "p4ss"
        assert opts["plaintext_mode"] is True
        assert cmd == ["command", "--arg", "value"]

    def test_at_secrets_token_preserved(self) -> None:
        opts, cmd = cli._parse_options(["cmd", "--file", "@SECRETS@"])
        assert cmd == ["cmd", "--file", "@SECRETS@"]

    def test_external_args_with_flags(self) -> None:
        opts, cmd = cli._parse_options(["-s", "cmd", "arg1", "--flag", "val"])
        assert opts["source_mode"] is True
        assert cmd == ["cmd", "arg1", "--flag", "val"]

    def test_file_missing_value(self) -> None:
        with pytest.raises(SystemExit):
            cli._parse_options(["--file"])

    def test_app_missing_value(self) -> None:
        with pytest.raises(SystemExit):
            cli._parse_options(["--app"])

    def test_no_comand_returns_empty(self) -> None:
        opts, cmd = cli._parse_options(["--source"])
        assert cmd == []


class TestMainBlock:
    def test_main_block(self, mocker: MockerFixture) -> None:
        dispatch = mocker.patch("kleys.modes.dispatch")
        mocker.patch.object(sys, "argv", ["kleys", "echo", "hello"])
        ns = dict(vars(cli))
        ns["__name__"] = "__main__"
        exec(compile(open(cli.__file__).read(), cli.__file__, "exec"), ns)
        dispatch.assert_called_once()


class TestMain:
    def test_empty_command_exits(self, mocker: MockerFixture) -> None:
        mocker.patch("kleys.modes.dispatch")
        with pytest.raises(SystemExit) as exc:
            cli.main([])
        assert exc.value.code == 1

    def test_dispatch_called(self, mocker: MockerFixture) -> None:
        dispatch = mocker.patch("kleys.modes.dispatch")
        cli.main(["echo", "hello"])
        dispatch.assert_called_once_with(
            command=["echo", "hello"],
            file=".env",
            app_name=mocker.ANY,
            source_mode=False,
            password=None,
            plaintext_mode=False,
        )

    def test_app_name_defaults_to_cwd(self, mocker: MockerFixture) -> None:
        dispatch = mocker.patch("kleys.modes.dispatch")
        cli.main(["run"])
        assert dispatch.call_args.kwargs["app_name"] != ""

    def test_all_options_passed_to_dispatch(
        self, mocker: MockerFixture
    ) -> None:
        dispatch = mocker.patch("kleys.modes.dispatch")
        cli.main(
            [
                "--file",
                "s.env",
                "--app",
                "myapp",
                "--source",
                "--password",
                "p@ss",
                "--plaintext",
                "cmd",
                "--ext",
                "val",
            ]
        )
        kwargs = dispatch.call_args.kwargs
        assert kwargs["file"] == "s.env"
        assert kwargs["app_name"] == "myapp"
        assert kwargs["source_mode"] is True
        assert kwargs["password"] == "p@ss"
        assert kwargs["plaintext_mode"] is True
        assert kwargs["command"] == ["cmd", "--ext", "val"]


class TestParseShowOptions:
    """Tests for _parse_show_options."""

    def test_no_args_defaults(self) -> None:
        opts = cli._parse_show_options([])
        assert opts == {"app_name": None, "password": None}

    def test_app_option(self) -> None:
        opts = cli._parse_show_options(["--app", "myapp"])
        assert opts["app_name"] == "myapp"

    def test_app_short(self) -> None:
        opts = cli._parse_show_options(["-a", "myapp"])
        assert opts["app_name"] == "myapp"

    def test_password_option(self) -> None:
        opts = cli._parse_show_options(["--password", "hunter2"])
        assert opts["password"] == "hunter2"

    def test_help_exits(self) -> None:
        with pytest.raises(SystemExit):
            cli._parse_show_options(["--help"])

    def test_help_h_exits(self) -> None:
        with pytest.raises(SystemExit):
            cli._parse_show_options(["-h"])

    def test_unknown_option_exits(self) -> None:
        with pytest.raises(SystemExit):
            cli._parse_show_options(["--unknown"])

    def test_app_missing_value(self) -> None:
        with pytest.raises(SystemExit):
            cli._parse_show_options(["--app"])

    def test_password_missing_value(self) -> None:
        with pytest.raises(SystemExit):
            cli._parse_show_options(["--password"])


class TestParseClearOptions:
    """Tests for _parse_clear_options."""

    def test_no_args_defaults(self) -> None:
        opts = cli._parse_clear_options([])
        assert opts == {"app_name": None}

    def test_app_option(self) -> None:
        opts = cli._parse_clear_options(["--app", "myapp"])
        assert opts["app_name"] == "myapp"

    def test_app_short(self) -> None:
        opts = cli._parse_clear_options(["-a", "myapp"])
        assert opts["app_name"] == "myapp"

    def test_help_exits(self) -> None:
        with pytest.raises(SystemExit):
            cli._parse_clear_options(["--help"])

    def test_help_h_exits(self) -> None:
        with pytest.raises(SystemExit):
            cli._parse_clear_options(["-h"])

    def test_unknown_option_exits(self) -> None:
        with pytest.raises(SystemExit):
            cli._parse_clear_options(["--unknown"])

    def test_app_missing_value(self) -> None:
        with pytest.raises(SystemExit):
            cli._parse_clear_options(["--app"])


class TestHandleShow:
    """Tests for _handle_show."""

    def test_encrypted_found_decrypts_and_displays(
        self, mocker: MockerFixture
    ) -> None:
        mocker.patch("kleys.keyring_.lookup", return_value="encrypted:b64==")
        mocker.patch(
            "kleys.cli.resolve_decrypt_password", return_value="thepassword"
        )
        mocker.patch(
            "kleys.crypto.decrypt", return_value="KEY=value\nSECRET=123"
        )
        mock_info = mocker.patch("kleys.cli.info")

        cli._handle_show(["--app", "myapp"])

        assert mock_info.call_count == 2
        mock_info.assert_any_call("Secrets for 'myapp':")
        mock_info.assert_any_call("KEY=value\nSECRET=123")

    def test_encrypted_found_no_password_exits(
        self, mocker: MockerFixture
    ) -> None:
        mocker.patch("kleys.keyring_.lookup", return_value="encrypted:b64==")
        mocker.patch("kleys.cli.resolve_decrypt_password", return_value=None)
        mock_error = mocker.patch("kleys.cli.error")

        with pytest.raises(SystemExit):
            cli._handle_show(["--app", "myapp"])

        mock_error.assert_called_once()
        assert "password" in mock_error.call_args[0][0].lower()

    def test_encrypted_found_decrypt_fails_exits(
        self, mocker: MockerFixture
    ) -> None:
        mocker.patch("kleys.keyring_.lookup", return_value="encrypted:b64==")
        mocker.patch(
            "kleys.cli.resolve_decrypt_password", return_value="thepassword"
        )
        mocker.patch("kleys.crypto.decrypt", return_value=None)
        mock_error = mocker.patch("kleys.cli.error")

        with pytest.raises(SystemExit):
            cli._handle_show(["--app", "myapp"])

        mock_error.assert_called_once()
        assert "decrypt" in mock_error.call_args[0][0].lower()

    def test_plaintext_found_displays(self, mocker: MockerFixture) -> None:
        mock_lookup = mocker.patch("kleys.keyring_.lookup")
        mock_lookup.side_effect = lambda key: (
            None if key.endswith("-encrypted") else "PLAIN=value"
        )
        mock_info = mocker.patch("kleys.cli.info")

        cli._handle_show(["--app", "myapp"])

        assert mock_info.call_count == 2
        mock_info.assert_any_call("Secrets for 'myapp' (plaintext):")
        mock_info.assert_any_call("PLAIN=value")

    def test_no_secrets_exits_with_error(self, mocker: MockerFixture) -> None:
        mocker.patch("kleys.keyring_.lookup", return_value=None)
        mock_warn = mocker.patch("kleys.cli.warn")

        with pytest.raises(SystemExit):
            cli._handle_show(["--app", "myapp"])

        mock_warn.assert_called_once()
        assert "No secrets found" in mock_warn.call_args[0][0]


class TestHandleClear:
    """Tests for _handle_clear."""

    def test_deletes_both_encrypted_and_plaintext(
        self, mocker: MockerFixture
    ) -> None:
        mocker.patch("kleys.keyring_.delete", return_value=True)
        mock_success = mocker.patch("kleys.cli.success")

        cli._handle_clear(["--app", "myapp"])

        assert mock_success.call_count == 2
        mock_success.assert_any_call("Deleted encrypted secrets for 'myapp'")
        mock_success.assert_any_call("Deleted plaintext secrets for 'myapp'")

    def test_only_encrypted_deleted(self, mocker: MockerFixture) -> None:
        mocker.patch("kleys.keyring_.delete", side_effect=[True, False])
        mock_success = mocker.patch("kleys.cli.success")

        cli._handle_clear(["--app", "myapp"])

        mock_success.assert_called_once_with(
            "Deleted encrypted secrets for 'myapp'"
        )

    def test_only_plaintext_deleted(self, mocker: MockerFixture) -> None:
        mocker.patch("kleys.keyring_.delete", side_effect=[False, True])
        mock_success = mocker.patch("kleys.cli.success")

        cli._handle_clear(["--app", "myapp"])

        mock_success.assert_called_once_with(
            "Deleted plaintext secrets for 'myapp'"
        )

    def test_nothing_to_delete_exits(self, mocker: MockerFixture) -> None:
        mocker.patch("kleys.keyring_.delete", side_effect=[False, False])
        mock_warn = mocker.patch("kleys.cli.warn")

        with pytest.raises(SystemExit):
            cli._handle_clear(["--app", "myapp"])

        mock_warn.assert_called_once()
        assert "No secrets found" in mock_warn.call_args[0][0]


class TestMainRouting:
    """Tests for main() subcommand routing."""

    def test_empty_args_exits(self, mocker: MockerFixture) -> None:
        mock_run = mocker.patch("kleys.cli._handle_run")
        mock_show = mocker.patch("kleys.cli._handle_show")
        mock_clear = mocker.patch("kleys.cli._handle_clear")

        with pytest.raises(SystemExit) as exc:
            cli.main([])
        assert exc.value.code == 1
        mock_run.assert_not_called()
        mock_show.assert_not_called()
        mock_clear.assert_not_called()

    def test_help_exits(self, mocker: MockerFixture) -> None:
        mock_run = mocker.patch("kleys.cli._handle_run")
        mock_show = mocker.patch("kleys.cli._handle_show")
        mock_clear = mocker.patch("kleys.cli._handle_clear")

        with pytest.raises(SystemExit) as exc:
            cli.main(["--help"])
        assert exc.value.code == 0
        mock_run.assert_not_called()
        mock_show.assert_not_called()
        mock_clear.assert_not_called()

    def test_run_subcommand(self, mocker: MockerFixture) -> None:
        mock_run = mocker.patch("kleys.cli._handle_run")
        mock_show = mocker.patch("kleys.cli._handle_show")
        mock_clear = mocker.patch("kleys.cli._handle_clear")

        cli.main(["run", "echo", "hello"])

        mock_run.assert_called_once_with(["echo", "hello"])
        mock_show.assert_not_called()
        mock_clear.assert_not_called()

    def test_show_subcommand(self, mocker: MockerFixture) -> None:
        mock_run = mocker.patch("kleys.cli._handle_run")
        mock_show = mocker.patch("kleys.cli._handle_show")
        mock_clear = mocker.patch("kleys.cli._handle_clear")

        cli.main(["show"])

        mock_show.assert_called_once_with([])
        mock_run.assert_not_called()
        mock_clear.assert_not_called()

    def test_clear_subcommand(self, mocker: MockerFixture) -> None:
        mock_run = mocker.patch("kleys.cli._handle_run")
        mock_show = mocker.patch("kleys.cli._handle_show")
        mock_clear = mocker.patch("kleys.cli._handle_clear")

        cli.main(["clear"])

        mock_clear.assert_called_once_with([])
        mock_run.assert_not_called()
        mock_show.assert_not_called()

    def test_backward_compat_treats_as_run(self, mocker: MockerFixture) -> None:
        mock_run = mocker.patch("kleys.cli._handle_run")
        mock_show = mocker.patch("kleys.cli._handle_show")
        mock_clear = mocker.patch("kleys.cli._handle_clear")

        cli.main(["echo", "hello"])

        mock_run.assert_called_once_with(["echo", "hello"])
        mock_show.assert_not_called()
        mock_clear.assert_not_called()
