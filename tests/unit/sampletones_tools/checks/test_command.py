from argparse import ArgumentParser, Namespace
from typing import Final, List

import pytest

from sampletones.commands.registry import COMMANDS
from sampletones.dispatcher import build_parser, dispatch
from sampletones_shared.command import Command
from sampletones_tools.checks import command
from sampletones_tools.checks.registry import GATES

GUARD: Final[str] = "sampletones_tools.checkout.require_checkout"


def _gate(name: str, calls: List[str]) -> Command:
    def configure(parser: ArgumentParser) -> None:
        parser.add_argument("--flag", action="store_true")

    def run(arguments: Namespace) -> int:
        calls.append(f"{name} {arguments.flag}")
        return 3

    return Command(name=name, help=f"{name} help", configure=configure, run=run)


class TestCheck:
    def test_every_gate_is_listed(self, capsys: pytest.CaptureFixture[str]) -> None:
        with pytest.raises(SystemExit) as leaving:
            build_parser(COMMANDS).parse_args(["check", "--help"])

        assert leaving.value.code == 0
        listing = capsys.readouterr().out
        assert GATES
        assert all(gate.name in listing for gate in GATES)

    def test_the_gate_named_runs_from_a_checkout(self, monkeypatch: pytest.MonkeyPatch) -> None:
        calls: List[str] = []
        guarded: List[str] = []
        monkeypatch.setattr(command, "GATES", (_gate("probe", calls),))
        monkeypatch.setattr(GUARD, guarded.append)

        assert dispatch(COMMANDS, ["check", "probe", "--flag"]) == 3
        assert calls == ["probe True"]
        assert guarded == ["check probe"]

    def test_an_unknown_check_is_refused(self) -> None:
        with pytest.raises(SystemExit) as leaving:
            dispatch(COMMANDS, ["check", "absent"])

        assert leaving.value.code == 2

    def test_a_check_is_required(self) -> None:
        with pytest.raises(SystemExit) as leaving:
            dispatch(COMMANDS, ["check"])

        assert leaving.value.code == 2

    def test_every_gate_has_a_name_of_its_own(self) -> None:
        names = [gate.name for gate in GATES]

        assert len(set(names)) == len(names)
