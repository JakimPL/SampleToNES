import argparse
import os
import sys
from typing import Final, Optional, Sequence, Tuple

from bootstrap.passes import Pass, run_passes
from bootstrap.processes import run
from bootstrap.repository import repository_root

DOCTESTS: Final[str] = "doctests"
SUITE: Final[str] = "suite"
BENCHMARKS: Final[str] = "benchmarks"
DEFAULT_WORKERS: Final[str] = "6"
PYTEST: Final[Tuple[str, ...]] = ("uv", "run", "python", "-m", "pytest")


def planned_passes(workers: str) -> Tuple[Pass, ...]:
    """The passes of a test run, in order: the doctests, the covered suite, the benchmarks.

    The covered suite runs across ``workers`` pytest workers. The benchmarks run last, serial,
    uncovered and with their output shown, so a measured duration is the code's own cost and
    its reading reaches the terminal.

    Args:
        workers: The worker count for the covered suite, or ``auto`` for one per processor.
    """
    return (
        Pass(
            DOCTESTS,
            "Running doctests...",
            (*PYTEST, "src/", "--doctest-modules", "--no-cov"),
        ),
        Pass(
            SUITE,
            "Running pytest with coverage...",
            (*PYTEST, "-n", workers, "--cov", "--ignore=tests/benchmarks"),
        ),
        Pass(
            BENCHMARKS,
            "Running benchmarks...",
            (*PYTEST, "tests/benchmarks", "--no-cov", "-s"),
        ),
    )


def selected(passes: Sequence[Pass], only: Optional[str]) -> Tuple[Pass, ...]:
    """The passes a run performs: all of them, or the one ``only`` names."""
    return tuple(current for current in passes if only is None or current.name == only)


def main(argv: Sequence[str]) -> int:
    """Runs the doctests, the covered suite and the benchmarks, and reports which failed."""
    parser = argparse.ArgumentParser(description="Run the SampleToNES tests.")
    parser.add_argument("--only", choices=(DOCTESTS, SUITE, BENCHMARKS), help="run one pass alone")
    parser.add_argument(
        "--workers",
        default=DEFAULT_WORKERS,
        help="pytest workers for the covered suite: a count, or auto for one per processor",
    )
    arguments = parser.parse_args(list(argv))

    failed = run_passes(
        selected(planned_passes(arguments.workers), arguments.only),
        root=repository_root(),
        runner=run,
        environment=os.environ,
    )
    if failed:
        print(f"Tests failed: {', '.join(failed)}.")
        return 1

    print("All tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
