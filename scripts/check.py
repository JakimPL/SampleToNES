import argparse
import os
import sys
from pathlib import Path
from typing import Final, Mapping, Optional, Sequence, Tuple

from bootstrap.checked_commits import clean_tree, mark_checked, short_commit
from bootstrap.layout import RUN_TESTS_SCRIPT, repository_root
from bootstrap.passes import Pass, run_passes
from bootstrap.processes import Runner, run

HOOKS: Final[str] = "pre-commit"
DOCTESTS: Final[str] = "doctests"
SUITE: Final[str] = "suite"
SCREENS: Final[str] = "screens"
TEST_PASSES: Final[Tuple[Tuple[str, str], ...]] = (
    (DOCTESTS, "the doctests"),
    (SUITE, "the covered suite"),
    (SCREENS, "the screen scenarios"),
)
RUN_HOOKS: Final[Tuple[str, ...]] = ("uv", "run", "pre-commit", "run", "--all-files")
UNCOMMITTED_FILES: Final[str] = (
    "The files differ from the last commit, so this check will mark no commit. "
    "Commit every change and run `make check` again to have the commit marked."
)
FAILED: Final[str] = "The check failed: {passes}. No commit is marked."
CHANGED_FILES: Final[str] = (
    "Every check passed, but the files differ from the last commit, so no commit is marked. "
    "Commit the changes and run `make check` again before pushing."
)
MARKED: Final[str] = "Commit {commit} passed every check and can be pushed."


def planned_checks(python: str) -> Tuple[Pass, ...]:
    """Every check a push waits for, in order: pre-commit over every file, then the doctests, the
    covered suite and the screen scenarios.

    These are the passes CI runs on a pull request. The hooks come first, since they answer in
    minutes and the tests take far longer. Each test pass is the command its make target runs, so
    a pass the check runs behaves as it does on its own.

    Args:
        python: The interpreter the test runner runs on.

    Returns:
        Tuple[Pass, ...]: The checks, in the order they run.
    """
    hooks = Pass(HOOKS, "Checking every file with pre-commit...", RUN_HOOKS)
    tests = (
        Pass(name, f"Checking {description}...", (python, RUN_TESTS_SCRIPT, name)) for name, description in TEST_PASSES
    )
    return (hooks, *tests)


def check_commit(
    root: Path,
    checks: Sequence[Pass],
    *,
    runner: Runner,
    environment: Mapping[str, str],
) -> int:
    """Runs every check and marks the commit they passed on, which lets a push of it through.

    Every check runs whatever the earlier ones reported, so one run shows everything that is wrong.
    A run over files that differ from the last commit says so as it starts, since the checks take
    long and that run marks nothing.

    Args:
        root: The repository, which every check runs in.
        checks: The checks, in order.
        runner: What runs them.
        environment: The variables they see.

    Returns:
        int: 1 where a check failed, 0 otherwise.
    """
    started_on = clean_tree(root)
    if started_on is None:
        print(UNCOMMITTED_FILES)

    failed = run_passes(checks, root=root, runner=runner, environment=environment)
    if failed:
        print(FAILED.format(passes=", ".join(failed)))
        return 1

    mark_unchanged_commit(root, started_on)
    return 0


def mark_unchanged_commit(root: Path, started_on: Optional[str]) -> None:
    """Marks the commit every check passed on, while the work tree holds the files the run started on.

    Args:
        root: The repository.
        started_on: The tree of the commit the run started on, or ``None`` where the work tree
            held other files.
    """
    if started_on is None or clean_tree(root) != started_on:
        print(CHANGED_FILES)
        return

    mark_checked(root, started_on)
    print(MARKED.format(commit=short_commit(root, "HEAD")))


def main(argv: Sequence[str]) -> int:
    """Runs every check a push waits for and marks the commit they passed on."""
    parser = argparse.ArgumentParser(description="Run every check a push waits for and mark the commit they passed on.")
    parser.parse_args(list(argv))

    return check_commit(
        repository_root(),
        planned_checks(sys.executable),
        runner=run,
        environment=os.environ,
    )


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
