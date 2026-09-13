from dataclasses import dataclass
from pathlib import Path
from typing import Tuple

import pytest

from tests.suite.base import BaseTestSuite
from tests.suite.bootstrap import RecordingRunner
from tests.suite.case import BaseRegularTestCase
from tests.suite.scripts import load_script

run_tests = load_script("run_tests.py")


class TestPlannedPasses:
    def test_every_pass_is_found_under_its_name(self) -> None:
        passes = run_tests.planned_passes(run_tests.DEFAULT_WORKERS)

        assert all(name == current.name for name, current in passes.items())
        assert set(passes) == {run_tests.SUITE, run_tests.DOCTESTS, run_tests.BENCHMARKS}

    def test_the_suite_is_covered_across_the_workers_and_leaves_the_benchmarks_out(self) -> None:
        command = run_tests.planned_passes("auto")[run_tests.SUITE].command

        assert command[-4:] == ("-n", "auto", "--cov", "--ignore=tests/benchmarks")

    def test_the_doctests_read_the_sources_uncovered(self) -> None:
        command = run_tests.planned_passes(run_tests.DEFAULT_WORKERS)[run_tests.DOCTESTS].command

        assert "--doctest-modules" in command
        assert "--no-cov" in command

    def test_the_benchmarks_run_serial_uncovered_and_show_their_readings(self) -> None:
        command = run_tests.planned_passes(run_tests.DEFAULT_WORKERS)[run_tests.BENCHMARKS].command

        assert "tests/benchmarks" in command
        assert "--no-cov" in command
        assert "-s" in command
        assert "-n" not in command


class TestRunPass:
    def test_the_pass_runs_from_the_repository(self, tmp_path: Path) -> None:
        runner = RecordingRunner({}, None)
        chosen = run_tests.planned_passes(run_tests.DEFAULT_WORKERS)[run_tests.DOCTESTS]

        assert run_tests.run_pass(chosen, tmp_path, runner=runner, environment={}) == 0
        assert runner.lines == [" ".join(chosen.command)]
        assert runner.commands[0].cwd == tmp_path

    def test_the_status_is_pytest_s_own(self, tmp_path: Path) -> None:
        chosen = run_tests.planned_passes("auto")[run_tests.SUITE]

        assert run_tests.run_pass(chosen, tmp_path, runner=RecordingRunner({"pytest": 5}, None), environment={}) == 5


class TestRefusedPasses(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        argv: Tuple[str, ...]

    test_cases = (
        TestCase(label="a missing pass", argv=()),
        TestCase(label="an unknown pass", argv=("everything",)),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_a_pass_outside_the_three_is_refused(self, test_case: TestCase) -> None:
        with pytest.raises(SystemExit) as exit_info:
            run_tests.main(test_case.argv)

        assert exit_info.value.code == 2
