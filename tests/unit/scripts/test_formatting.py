from pathlib import Path

import pytest

from bootstrap.layout import FORMATTED_PATHS
from tests.suite.bootstrap import RecordingRunner
from tests.suite.scripts import load_script

formatting = load_script("formatting.py")


class TestFormattedPaths:
    def test_the_checked_paths_and_the_tests_are_formatted_by_default(self) -> None:
        assert formatting.formatted_paths(()) == FORMATTED_PATHS

    def test_named_paths_replace_the_trees(self) -> None:
        assert formatting.formatted_paths(("scripts/lint.py",)) == ("scripts/lint.py",)


class TestFormatCode:
    def test_isort_runs_before_black(self, tmp_path: Path) -> None:
        runner = RecordingRunner({}, None)

        formatting.format_code(tmp_path, FORMATTED_PATHS, runner=runner, environment={})

        assert runner.lines == [
            " ".join((*formatting.ISORT, *FORMATTED_PATHS)),
            " ".join((*formatting.BLACK, *FORMATTED_PATHS)),
        ]

    def test_a_failing_formatter_stops_the_run(self, tmp_path: Path) -> None:
        runner = RecordingRunner({"isort": 1}, None)

        with pytest.raises(SystemExit, match="isort"):
            formatting.format_code(tmp_path, FORMATTED_PATHS, runner=runner, environment={})

        assert len(runner.lines) == 1
