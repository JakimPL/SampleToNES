import argparse
import os
import sys
from pathlib import Path
from typing import Dict, Final, Mapping, Sequence, Tuple

from bootstrap.layout import repository_root
from bootstrap.passes import Pass
from bootstrap.processes import Runner, run

SUITE: Final[str] = "suite"
DOCTESTS: Final[str] = "doctests"
BENCHMARKS: Final[str] = "benchmarks"
DEFAULT_WORKERS: Final[str] = "6"
PYTEST: Final[Tuple[str, ...]] = ("uv", "run", "python", "-m", "pytest")


def planned_passes(workers: str) -> Dict[str, Pass]:
    """The passes a test run is made of, by name: the covered suite, the doctests, the benchmarks.

    Each pass is a target and a hook of its own, so a failure names the pass it belongs to. The
    covered suite runs across ``workers`` pytest workers. The benchmarks run serial, uncovered
    and with their output shown, so a measured duration is the code's own cost and its reading
    reaches the terminal.

    Args:
        workers: The worker count for the covered suite, or ``auto`` for one per processor.

    Returns:
        Dict[str, Pass]: Every pass, under its name.
    """
    passes = (
        Pass(
            SUITE,
            "Running pytest with coverage...",
            (*PYTEST, "-n", workers, "--cov", "--ignore=tests/benchmarks"),
        ),
        Pass(
            DOCTESTS,
            "Running doctests...",
            (*PYTEST, "src/", "--doctest-modules", "--no-cov"),
        ),
        Pass(
            BENCHMARKS,
            "Running benchmarks...",
            (*PYTEST, "tests/benchmarks", "--no-cov", "-s"),
        ),
    )
    return {current.name: current for current in passes}


def run_pass(
    chosen: Pass,
    root: Path,
    *,
    runner: Runner,
    environment: Mapping[str, str],
) -> int:
    """Announces one pass and runs it from the repository root.

    Args:
        chosen: The pass.
        root: The repository.
        runner: What runs the pass.
        environment: The variables pytest sees.

    Returns:
        int: The status pytest exited with.
    """
    print(chosen.announcement)
    return runner(chosen.command, cwd=root, environment=environment, quiet=False)


def main(argv: Sequence[str]) -> int:
    """Runs one pass of the tests and exits with the status pytest gave it."""
    parser = argparse.ArgumentParser(description="Run one pass of the SampleToNES tests.")
    parser.add_argument("name", choices=(SUITE, DOCTESTS, BENCHMARKS), help="the pass to run")
    parser.add_argument(
        "--workers",
        default=DEFAULT_WORKERS,
        help="pytest workers for the covered suite: a count, or auto for one per processor",
    )
    arguments = parser.parse_args(list(argv))

    return run_pass(
        planned_passes(arguments.workers)[arguments.name],
        repository_root(),
        runner=run,
        environment=os.environ,
    )


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
