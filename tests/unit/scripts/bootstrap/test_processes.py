import os
import sys
from pathlib import Path

import pytest

from bootstrap.processes import expect_success, run
from tests.suite.bootstrap import RecordingRunner


class TestRun:
    def test_the_status_is_the_command_s_own(self, tmp_path: Path) -> None:
        status = run(
            (sys.executable, "-c", "raise SystemExit(3)"),
            cwd=tmp_path,
            environment={},
            quiet=True,
        )

        assert status == 3

    def test_what_the_script_printed_leads_the_command_s_output(
        self,
        tmp_path: Path,
        capfd: pytest.CaptureFixture[str],
    ) -> None:
        print("before")
        run(
            (sys.executable, "-c", "print('inside')"),
            cwd=tmp_path,
            environment=os.environ,
            quiet=False,
        )

        assert capfd.readouterr().out.splitlines() == ["before", "inside"]


class TestExpectSuccess:
    def test_a_succeeding_command_passes(self, tmp_path: Path) -> None:
        runner = RecordingRunner({}, None)

        expect_success(runner, ("echo", "hello"), cwd=tmp_path, environment={"KEY": "value"})

        assert runner.lines == ["echo hello"]
        assert runner.commands[0].environment == {"KEY": "value"}
        assert not runner.commands[0].quiet

    def test_a_failing_command_stops_the_script_naming_it(self, tmp_path: Path) -> None:
        runner = RecordingRunner({"echo": 2}, None)

        with pytest.raises(SystemExit, match="echo hello exited with status 2"):
            expect_success(runner, ("echo", "hello"), cwd=tmp_path, environment={})
