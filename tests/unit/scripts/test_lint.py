from pathlib import Path

import pytest

from tests.suite.bootstrap import RecordingRunner
from tests.suite.scripts import load_script

lint = load_script("lint.py")


class TestLinters:
    def test_mypy_reads_its_configuration_and_pylint_sweeps_the_trees(self) -> None:
        mypy, pylint = lint.linters(())

        assert mypy.command == ("uv", "run", "python", "-m", lint.MYPY)
        assert pylint.command == ("uv", "run", "python", "-m", lint.PYLINT, *lint.LINTED_TREES)

    def test_named_paths_reach_both(self) -> None:
        mypy, pylint = lint.linters(("scripts/lint.py",))

        assert mypy.command[-1] == "scripts/lint.py"
        assert pylint.command[-1] == "scripts/lint.py"


class TestChosenLinters:
    def test_both_linters_run_by_default(self) -> None:
        assert [linter.name for linter in lint.chosen_linters((), mypy=False, pylint=False)] == [lint.MYPY, lint.PYLINT]

    def test_a_flag_picks_one_linter(self) -> None:
        assert [linter.name for linter in lint.chosen_linters((), mypy=False, pylint=True)] == [lint.PYLINT]


class TestLintCode:
    def test_every_linter_passing_is_reported(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        runner = RecordingRunner({}, None)

        assert lint.lint_code(tmp_path, lint.linters(()), runner=runner, environment={}) == 0
        assert len(runner.lines) == 2
        assert "All linting checks passed." in capsys.readouterr().out

    def test_a_failing_linter_stops_nothing_and_is_named(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        runner = RecordingRunner({lint.MYPY: 1}, None)

        assert lint.lint_code(tmp_path, lint.linters(()), runner=runner, environment={}) == 1
        assert len(runner.lines) == 2
        assert f"Linting failed: {lint.MYPY}." in capsys.readouterr().out
