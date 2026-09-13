import pytest

from tests.suite.bootstrap import RecordingRunner
from tests.suite.scripts import load_script

lint = load_script("lint.py")


class TestLinters:
    def test_mypy_reads_its_configuration_and_pylint_sweeps_the_trees(self) -> None:
        mypy, pylint = lint.linters(())

        assert mypy.command == ("uv", "run", "python", "-m", "mypy")
        assert pylint.command == ("uv", "run", "python", "-m", "pylint", "src", "scripts")

    def test_named_paths_reach_both(self) -> None:
        mypy, pylint = lint.linters(("scripts/lint.py",))

        assert mypy.command[-1] == "scripts/lint.py"
        assert pylint.command[-1] == "scripts/lint.py"


class TestMain:
    def test_both_linters_run_by_default(
        self,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        runner = RecordingRunner({}, None)
        monkeypatch.setattr(lint, "run", runner)

        assert lint.main([]) == 0
        assert [line.split()[-1] for line in runner.lines[:1]] == ["mypy"]
        assert "pylint" in runner.lines[1]
        assert "All linting checks passed." in capsys.readouterr().out

    def test_a_flag_picks_one_linter(self, monkeypatch: pytest.MonkeyPatch) -> None:
        runner = RecordingRunner({}, None)
        monkeypatch.setattr(lint, "run", runner)

        assert lint.main(["--pylint"]) == 0
        assert len(runner.lines) == 1
        assert "pylint src scripts" in runner.lines[0]

    def test_a_failing_linter_stops_nothing_and_is_named(
        self,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        runner = RecordingRunner({"mypy": 1}, None)
        monkeypatch.setattr(lint, "run", runner)

        assert lint.main([]) == 1
        assert len(runner.lines) == 2
        assert "Linting failed: mypy." in capsys.readouterr().out
