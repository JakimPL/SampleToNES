from pathlib import Path

import pytest

from bootstrap.passes import Pass, run_passes
from tests.suite.bootstrap import RecordingRunner

PASSES = (
    Pass("first", "First...", ("first", "command")),
    Pass("second", "Second...", ("second", "command")),
    Pass("third", "Third...", ("third", "command")),
)


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
