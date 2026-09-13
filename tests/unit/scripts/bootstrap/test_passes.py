from pathlib import Path

import pytest

from bootstrap.passes import Pass, run_pass, run_passes
from tests.suite.bootstrap import RecordingRunner

PASSES = (
    Pass("first", "First...", ("first", "command")),
    Pass("second", "Second...", ("second", "command")),
    Pass("third", "Third...", ("third", "command")),
)


class TestRunPass:
    def test_the_pass_is_announced_and_run_from_the_repository(
        self,
        capsys: pytest.CaptureFixture[str],
        tmp_path: Path,
    ) -> None:
        runner = RecordingRunner({}, None)

        assert run_pass(PASSES[0], root=tmp_path, runner=runner, environment={}) == 0
        assert runner.lines == ["first command"]
        assert runner.commands[0].cwd == tmp_path
        assert capsys.readouterr().out == "First...\n"

    def test_the_status_is_the_command_s_own(self, tmp_path: Path) -> None:
        assert run_pass(PASSES[1], root=tmp_path, runner=RecordingRunner({"second": 5}, None), environment={}) == 5


class TestRunPasses:
    def test_every_pass_runs_and_the_failed_ones_are_named(self, capsys: pytest.CaptureFixture[str]) -> None:
        runner = RecordingRunner({"second": 1}, None)

        failed = run_passes(PASSES, root=Path("/repository"), runner=runner, environment={"PATH": "/usr/bin"})

        assert failed == ["second"]
        assert runner.lines == ["first command", "second command", "third command"]
        assert all(recorded.cwd == Path("/repository") for recorded in runner.commands)
        assert all(recorded.environment == {"PATH": "/usr/bin"} for recorded in runner.commands)
        assert capsys.readouterr().out == "First...\nSecond...\nThird...\n"

    def test_a_clean_run_names_nothing(self) -> None:
        runner = RecordingRunner({}, None)

        assert run_passes(PASSES, root=Path("/repository"), runner=runner, environment={}) == []
