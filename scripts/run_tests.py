import argparse
import os
import sys
from typing import Dict, Final, Sequence, Tuple

from bootstrap.layout import BENCHMARKS_DIRECTORY, SCREENS_DIRECTORY, SOURCE_DIRECTORY, repository_root
from bootstrap.passes import Pass, run_pass
from bootstrap.processes import run

SUITE: Final[str] = "suite"
DOCTESTS: Final[str] = "doctests"
BENCHMARKS: Final[str] = "benchmarks"
SCREENS: Final[str] = "screens"
DEFAULT_WORKERS: Final[str] = "6"
SCREEN_WORKERS: Final[str] = "4"
PYTEST: Final[Tuple[str, ...]] = ("uv", "run", "python", "-m", "pytest")


def planned_passes(workers: str, screen_workers: str) -> Dict[str, Pass]:
    """The passes a test run is made of, by name: the covered suite, the doctests, the benchmarks
    and the screen scenarios.

    Each pass is a target and a hook of its own, so a failure names the pass it belongs to. The
    covered suite runs across ``workers`` pytest workers. The benchmarks run serial, uncovered
    and with their output shown, so a measured duration is the code's own cost and its reading
    reaches the terminal. The screen scenarios drive the running application on a display of
    each worker's own, each scenario in a process of its own, so they run uncovered across
    ``screen_workers`` workers, each drawing its frames on the processor.

    Args:
        workers: The worker count for the covered suite, or ``auto`` for one per processor.
        screen_workers: The worker count for the screen scenarios, each worker drawing one
            application at a time.

    Returns:
        Dict[str, Pass]: Every pass, under its name.
    """
    passes = (
        Pass(
            SUITE,
            "Running pytest with coverage...",
            (
                *PYTEST,
                "-n",
                workers,
                "--cov",
                f"--ignore={BENCHMARKS_DIRECTORY}",
                f"--ignore={SCREENS_DIRECTORY}",
            ),
        ),
        Pass(
            DOCTESTS,
            "Running doctests...",
            (*PYTEST, SOURCE_DIRECTORY, "--doctest-modules", "--no-cov"),
        ),
        Pass(
            BENCHMARKS,
            "Running benchmarks...",
            (*PYTEST, BENCHMARKS_DIRECTORY, "--no-cov", "-s"),
        ),
        Pass(
            SCREENS,
            "Running screen scenarios...",
            (*PYTEST, SCREENS_DIRECTORY, "-n", screen_workers, "--no-cov"),
        ),
    )
    return {current.name: current for current in passes}


def main(argv: Sequence[str]) -> int:
    """Runs one pass of the tests and exits with the status pytest gave it."""
    parser = argparse.ArgumentParser(description="Run one pass of the SampleToNES tests.")
    parser.add_argument(
        "name",
        choices=tuple(planned_passes(DEFAULT_WORKERS, SCREEN_WORKERS)),
        help="the pass to run",
    )
    parser.add_argument(
        "--workers",
        default=DEFAULT_WORKERS,
        help="pytest workers for the covered suite: a count, or auto for one per processor",
    )
    parser.add_argument(
        "--screen-workers",
        default=SCREEN_WORKERS,
        help="pytest workers for the screen scenarios, each drawing one application at a time",
    )
    arguments = parser.parse_args(list(argv))

    return run_pass(
        planned_passes(arguments.workers, arguments.screen_workers)[arguments.name],
        root=repository_root(),
        runner=run,
        environment=os.environ,
    )


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
