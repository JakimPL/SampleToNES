import pytest

from tests.suite.bootstrap import RecordingRunner
from tests.suite.scripts import load_script

run_tests = load_script("run_tests.py")


class TestPlannedPasses:
    def test_the_doctests_run_first_and_the_benchmarks_last(self) -> None:
        passes = run_tests.planned_passes("6")

        assert [current.name for current in passes] == ["doctests", "suite", "benchmarks"]
        assert "--doctest-modules" in passes[0].command
        assert passes[1].command[-4:] == ("-n", "6", "--cov", "--ignore=tests/benchmarks")
        assert "--no-cov" in passes[2].command
        assert "-s" in passes[2].command


class TestSelected:
    def test_a_name_keeps_one_pass(self) -> None:
        passes = run_tests.planned_passes("6")

        assert run_tests.selected(passes, "suite") == (passes[1],)
        assert run_tests.selected(passes, None) == passes


class TestMain:
    def test_only_runs_the_named_pass(
        self,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        runner = RecordingRunner({}, None)
        monkeypatch.setattr(run_tests, "run", runner)

        assert run_tests.main(["--only", "benchmarks"]) == 0
        assert len(runner.lines) == 1
        assert "tests/benchmarks" in runner.lines[0]
        assert "All tests passed." in capsys.readouterr().out

    def test_a_failing_pass_stops_nothing_and_is_named(
        self,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        runner = RecordingRunner({"--doctest-modules": 1}, None)
        monkeypatch.setattr(run_tests, "run", runner)

        assert run_tests.main(["--workers", "auto"]) == 1
        assert len(runner.lines) == 3
        assert "-n auto" in runner.lines[1]
        assert "Tests failed: doctests." in capsys.readouterr().out
