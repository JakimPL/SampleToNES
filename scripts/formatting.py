import argparse
import os
import sys
from pathlib import Path
from typing import Final, Mapping, Sequence, Tuple

from bootstrap.layout import SOURCE_DIRECTORY, repository_root
from bootstrap.processes import Runner, expect_success, run

FORMATTED_TREES: Final[Tuple[str, ...]] = (SOURCE_DIRECTORY, "tests", "scripts")
ISORT: Final[Tuple[str, ...]] = ("uv", "run", "python", "-m", "isort")
BLACK: Final[Tuple[str, ...]] = ("uv", "run", "python", "-m", "black")


def format_code(
    root: Path,
    paths: Sequence[str],
    *,
    runner: Runner,
    environment: Mapping[str, str],
) -> None:
    """Sorts the imports and formats the code under ``paths``, isort first so black settles the result.

    Args:
        root: The repository, which the formatters run in.
        paths: The files or directories formatted.
        runner: What runs the formatters.
        environment: The variables the formatters see.

    Raises:
        SystemExit: If a formatter fails, before the next one runs.
    """
    print("Formatting imports with isort...")
    expect_success(runner, (*ISORT, *paths), cwd=root, environment=environment)
    print("Formatting code with black...")
    expect_success(runner, (*BLACK, *paths), cwd=root, environment=environment)


def formatted_paths(named: Sequence[str]) -> Tuple[str, ...]:
    """The paths a run formats: the ones named, or the source, test and script trees."""
    return tuple(named) or FORMATTED_TREES


def main(argv: Sequence[str]) -> int:
    """Formats the source, test and script trees, or the paths named."""
    parser = argparse.ArgumentParser(description="Format the SampleToNES code with isort and black.")
    parser.add_argument("paths", nargs="*", help="files or directories to format in place of the whole trees")
    arguments = parser.parse_args(list(argv))

    format_code(
        repository_root(),
        formatted_paths(tuple(arguments.paths)),
        runner=run,
        environment=os.environ,
    )
    print("Code formatting complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
