from argparse import ArgumentParser, Namespace
from dataclasses import FrozenInstanceError

import pytest

from sampletones_shared.command import Command


def _configure(parser: ArgumentParser) -> None:
    parser.add_argument("--flag", action="store_true")


def _run(arguments: Namespace) -> int:
    return 3 if arguments.flag else 0


class TestCommand:
    def test_a_command_carries_its_parser_and_its_work(self) -> None:
        command = Command(name="probe", help="probe the thing", configure=_configure, run=_run)
        parser = ArgumentParser()

        command.configure(parser)

        assert command.run(parser.parse_args(["--flag"])) == 3
        assert command.run(parser.parse_args([])) == 0

    def test_a_command_is_settled_once_declared(self) -> None:
        command = Command(name="probe", help="probe the thing", configure=_configure, run=_run)

        with pytest.raises(FrozenInstanceError):
            command.name = "other"  # type: ignore[misc]
