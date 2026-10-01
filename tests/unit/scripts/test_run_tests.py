from dataclasses import dataclass
from typing import Tuple

import pytest

from bootstrap.layout import BENCHMARKS_DIRECTORY, SCREENS_DIRECTORY
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase
from tests.suite.scripts import load_script

run_tests = load_script("run_tests.py")


class TestPlannedPasses:
    def test_every_pass_is_found_under_its_name(self) -> None:
        passes = run_tests.planned_passes(run_tests.DEFAULT_WORKERS)

        assert all(name == current.name for name, current in passes.items())
        assert set(passes) == {run_tests.SUITE, run_tests.DOCTESTS, run_tests.BENCHMARKS, run_tests.SCREENS}

    def test_the_suite_is_covered_across_the_workers_and_leaves_the_other_passes_out(self) -> None:
        command = run_tests.planned_passes("auto")[run_tests.SUITE].command

        assert command[-5:] == (
            "-n",
            "auto",
            "--cov",
            f"--ignore={BENCHMARKS_DIRECTORY}",
            f"--ignore={SCREENS_DIRECTORY}",
        )

    def test_the_screen_scenarios_run_across_their_own_workers_uncovered(self) -> None:
        command = run_tests.planned_passes("auto")[run_tests.SCREENS].command

        assert SCREENS_DIRECTORY in command
        assert command[-3:] == ("-n", run_tests.SCREEN_WORKERS, "--no-cov")

    def test_the_doctests_read_the_sources_uncovered(self) -> None:
        command = run_tests.planned_passes(run_tests.DEFAULT_WORKERS)[run_tests.DOCTESTS].command

        assert "--doctest-modules" in command
        assert "--no-cov" in command

    def test_the_benchmarks_run_serial_uncovered_and_show_their_readings(self) -> None:
        command = run_tests.planned_passes(run_tests.DEFAULT_WORKERS)[run_tests.BENCHMARKS].command

        assert BENCHMARKS_DIRECTORY in command
        assert "--no-cov" in command
        assert "-s" in command
        assert "-n" not in command


class TestRefusedPasses(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        argv: Tuple[str, ...]

    test_cases = (
        TestCase(label="a missing pass", argv=()),
        TestCase(label="an unknown pass", argv=("everything",)),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_a_pass_outside_the_planned_ones_is_refused(self, test_case: TestCase) -> None:
        with pytest.raises(SystemExit) as exit_info:
            run_tests.main(test_case.argv)

        assert exit_info.value.code == 2
