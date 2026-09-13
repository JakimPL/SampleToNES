import pytest

from tests.suite.bootstrap import RecordingRunner
from tests.suite.scripts import load_script

formatting = load_script("formatting.py")


class TestMain:
    def test_isort_runs_before_black_over_the_three_trees(
        self,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        runner = RecordingRunner({}, None)
        monkeypatch.setattr(formatting, "run", runner)

        assert formatting.main([]) == 0
        assert runner.lines == [
            "uv run python -m isort src tests scripts",
            "uv run python -m black src tests scripts",
        ]
        assert "Code formatting complete." in capsys.readouterr().out

    def test_named_paths_replace_the_trees(self, monkeypatch: pytest.MonkeyPatch) -> None:
        runner = RecordingRunner({}, None)
        monkeypatch.setattr(formatting, "run", runner)

        assert formatting.main(["scripts/lint.py"]) == 0
        assert all(line.endswith(" scripts/lint.py") for line in runner.lines)

    def test_a_failing_formatter_stops_the_run(self, monkeypatch: pytest.MonkeyPatch) -> None:
        runner = RecordingRunner({"isort": 1}, None)
        monkeypatch.setattr(formatting, "run", runner)

        with pytest.raises(SystemExit, match="isort"):
            formatting.main([])

        assert len(runner.lines) == 1
