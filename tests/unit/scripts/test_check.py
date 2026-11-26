from dataclasses import dataclass
from typing import Callable, Final, Sequence

import pytest

from bootstrap.checked_commits import checked_trees, is_checked, short_commit
from bootstrap.layout import RUN_TESTS_SCRIPT
from tests.suite.base import BaseTestSuite
from tests.suite.bootstrap import RecordingRunner
from tests.suite.case import BaseRegularTestCase
from tests.suite.git import FIRST_FILE, ScratchRepository
from tests.suite.scripts import load_script

check = load_script("check.py")
run_tests = load_script("run_tests.py")

PYTHON: Final[str] = "/usr/bin/python3"
CHECKS = check.planned_checks(PYTHON, ())
FEWER_WORKERS: Final[str] = "2"
ONE_SCREEN_WORKER: Final[str] = "1"
FAILING_SUITE: Final[str] = f"{RUN_TESTS_SCRIPT} {check.SUITE}"


def _edit(repository: ScratchRepository) -> None:
    repository.write(FIRST_FILE, "VALUE = 2\n")


def _commit_an_edit(repository: ScratchRepository) -> None:
    _edit(repository)
    repository.commit("Changed: the value")


def _during_the_suite(
    repository: ScratchRepository,
    change: Callable[[ScratchRepository], None],
) -> Callable[[Sequence[str]], None]:
    def on_run(command: Sequence[str]) -> None:
        if check.SUITE in command:
            change(repository)

    return on_run


class TestPlannedChecks:
    def test_pre_commit_runs_first_over_every_file(self) -> None:
        hooks = CHECKS[0]

        assert hooks.name == check.HOOKS
        assert hooks.command == check.RUN_HOOKS
        assert "--all-files" in hooks.command

    def test_the_doctests_the_suite_and_the_screens_follow_through_the_test_runner(self) -> None:
        tests = CHECKS[1:]

        assert [current.name for current in tests] == [check.DOCTESTS, check.SUITE, check.SCREENS]
        assert all(current.command == (PYTHON, RUN_TESTS_SCRIPT, current.name) for current in tests)

    def test_every_test_pass_is_one_the_test_runner_plans(self) -> None:
        planned = run_tests.planned_passes(run_tests.DEFAULT_WORKERS, run_tests.SCREEN_WORKERS)

        assert {current.name for current in CHECKS[1:]} <= set(planned)

    def test_worker_counts_given_to_the_check_reach_every_test_pass(self) -> None:
        options = check.worker_options(FEWER_WORKERS, ONE_SCREEN_WORKER)

        tests = check.planned_checks(PYTHON, options)[1:]

        assert options == (check.WORKERS_OPTION, FEWER_WORKERS, check.SCREEN_WORKERS_OPTION, ONE_SCREEN_WORKER)
        assert all(current.command == (PYTHON, RUN_TESTS_SCRIPT, current.name, *options) for current in tests)

    def test_a_worker_count_left_out_keeps_the_test_runner_s_default(self) -> None:
        assert check.worker_options(None, None) == ()
        assert check.worker_options(None, ONE_SCREEN_WORKER) == (check.SCREEN_WORKERS_OPTION, ONE_SCREEN_WORKER)

    def test_the_test_runner_reads_the_worker_counts_the_check_forwards(self) -> None:
        options = check.worker_options(FEWER_WORKERS, ONE_SCREEN_WORKER)

        arguments = run_tests.argument_parser().parse_args([check.SUITE, *options])

        assert (arguments.workers, arguments.screen_workers) == (FEWER_WORKERS, ONE_SCREEN_WORKER)


class TestCheckCommit:
    def test_every_check_passing_on_a_commit_marks_it(
        self,
        repository: ScratchRepository,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        runner = RecordingRunner({}, None)

        assert check.check_commit(repository.root, CHECKS, runner=runner, environment={}) == 0
        assert runner.lines == [" ".join(current.command) for current in CHECKS]
        assert is_checked(repository.root, "HEAD")
        assert check.MARKED.format(commit=short_commit(repository.root, "HEAD")) in capsys.readouterr().out

    def test_a_failed_check_is_named_after_every_check_ran_and_nothing_is_marked(
        self,
        repository: ScratchRepository,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        runner = RecordingRunner({FAILING_SUITE: 1}, None)

        assert check.check_commit(repository.root, CHECKS, runner=runner, environment={}) == 1
        assert len(runner.commands) == len(CHECKS)
        assert checked_trees(repository.root) == []
        assert check.FAILED.format(passes=check.SUITE) in capsys.readouterr().out

    def test_a_run_over_uncommitted_files_says_so_as_it_starts_and_marks_nothing(
        self,
        repository: ScratchRepository,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        _edit(repository)

        assert check.check_commit(repository.root, CHECKS, runner=RecordingRunner({}, None), environment={}) == 0

        output = capsys.readouterr().out
        assert output.startswith(check.UNCOMMITTED_FILES)
        assert check.CHANGED_FILES in output
        assert checked_trees(repository.root) == []


class TestFilesChangedDuringTheCheck(BaseTestSuite):
    """The checks passed on files that are no longer the commit's, so the run marks nothing."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        change: Callable[[ScratchRepository], None]

    test_cases = (
        TestCase(label="an_edited_file", change=_edit),
        TestCase(label="a_new_commit", change=_commit_an_edit),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_a_change_while_the_checks_run_marks_no_commit(
        self,
        repository: ScratchRepository,
        capsys: pytest.CaptureFixture[str],
        test_case: TestCase,
    ) -> None:
        runner = RecordingRunner({}, _during_the_suite(repository, test_case.change))

        assert check.check_commit(repository.root, CHECKS, runner=runner, environment={}) == 0
        assert checked_trees(repository.root) == []
        assert check.CHANGED_FILES in capsys.readouterr().out
