from argparse import ArgumentParser, Namespace
from typing import List, Tuple

import pytest

from sampletones.dispatcher import DEFAULT_COMMAND, DEVELOPER_GUIDE, build_parser, dispatch
from sampletones_shared.application import SAMPLETONES_NAME_VERSION
from sampletones_shared.command import Command


def _command(name: str, calls: List[Tuple[str, bool]]) -> Command:
    def configure(parser: ArgumentParser) -> None:
        parser.add_argument("--flag", action="store_true")

    def run(arguments: Namespace) -> int:
        calls.append((name, arguments.flag))
        return 3

    return Command(name=name, help=f"{name} help", configure=configure, run=run)


class TestBuildParser:
    def test_two_commands_sharing_a_name_are_refused(self) -> None:
        calls: List[Tuple[str, bool]] = []

        with pytest.raises(ValueError, match="share a name: twin"):
            build_parser((_command("twin", calls), _command("twin", calls)))

    def test_the_version_is_a_flag_of_the_entry(self, capsys: pytest.CaptureFixture[str]) -> None:
        parser = build_parser((_command(DEFAULT_COMMAND, []),))

        with pytest.raises(SystemExit) as leaving:
            parser.parse_args(["--version"])

        assert leaving.value.code == 0
        assert SAMPLETONES_NAME_VERSION in capsys.readouterr().out

    def test_the_listing_says_where_the_developer_commands_run_and_what_lists_them(self) -> None:
        listing = " ".join(build_parser((_command("first", []),)).format_help().split())

        assert "uv run sampletones" in listing
        assert DEVELOPER_GUIDE in listing

    def test_every_command_is_listed_with_its_help(self) -> None:
        parser = build_parser((_command("first", []), _command("second", [])))

        listing = parser.format_help()

        assert "first help" in listing
        assert "second help" in listing


class TestDispatch:
    def test_no_arguments_run_the_default_command(self) -> None:
        calls: List[Tuple[str, bool]] = []

        assert dispatch((_command(DEFAULT_COMMAND, calls), _command("other", calls)), []) == 3
        assert calls == [(DEFAULT_COMMAND, False)]

    def test_a_named_command_runs_with_its_arguments(self) -> None:
        calls: List[Tuple[str, bool]] = []

        assert dispatch((_command(DEFAULT_COMMAND, calls), _command("other", calls)), ["other", "--flag"]) == 3
        assert calls == [("other", True)]

    def test_an_unknown_command_is_refused(self) -> None:
        with pytest.raises(SystemExit) as leaving:
            dispatch((_command(DEFAULT_COMMAND, []),), ["absent"])

        assert leaving.value.code == 2
