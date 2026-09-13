import argparse
import os
import sys
from pathlib import Path
from typing import Final, Mapping, Sequence, Set, Tuple

from bootstrap.layout import SOURCE_DIRECTORY, repository_root
from bootstrap.passes import Pass, run_passes
from bootstrap.processes import Runner, run

MYPY: Final[str] = "mypy"
PYLINT: Final[str] = "pylint"
LINTED_TREES: Final[Tuple[str, ...]] = (SOURCE_DIRECTORY, "scripts")


def linters(paths: Sequence[str]) -> Tuple[Pass, ...]:
    """Mypy and pylint, in that order, over ``paths``.

    Without paths, mypy reads the files ``pyproject.toml`` configures and pylint sweeps the
    source and script trees.
    """
    return (
        Pass(
            MYPY,
            "Running type checking with mypy...",
            ("uv", "run", "python", "-m", MYPY, *paths),
        ),
        Pass(
            PYLINT,
            "Running linting with pylint...",
            ("uv", "run", "python", "-m", PYLINT, *(paths or LINTED_TREES)),
        ),
    )


def lint_code(
    root: Path,
    passes: Sequence[Pass],
    *,
    runner: Runner,
    environment: Mapping[str, str],
) -> int:
    """Runs every linter asked for and names the ones that failed.

    Args:
        root: The repository, which the linters run in.
        passes: The linters, in order.
        runner: What runs them.
        environment: The variables they see.

    Returns:
        int: 0 where every linter passed, 1 otherwise.
    """
    failed = run_passes(passes, root=root, runner=runner, environment=environment)
    if failed:
        print(f"Linting failed: {', '.join(failed)}.")
        return 1

    print("All linting checks passed.")
    return 0


def chosen_linters(paths: Sequence[str], *, mypy: bool, pylint: bool) -> Tuple[Pass, ...]:
    """The linters a run asks for: the ones flagged, or both where none is."""
    chosen: Set[str] = {name for name, wanted in ((MYPY, mypy), (PYLINT, pylint)) if wanted}
    return tuple(linter for linter in linters(paths) if not chosen or linter.name in chosen)


def main(argv: Sequence[str]) -> int:
    """Type checks and lints the code, and reports which linter failed."""
    parser = argparse.ArgumentParser(description="Type check and lint the SampleToNES code.")
    parser.add_argument("--mypy", action="store_true", help="run mypy alone")
    parser.add_argument("--pylint", action="store_true", help="run pylint alone")
    parser.add_argument("paths", nargs="*", help="files or directories to lint in place of the whole trees")
    arguments = parser.parse_args(list(argv))

    return lint_code(
        repository_root(),
        chosen_linters(tuple(arguments.paths), mypy=arguments.mypy, pylint=arguments.pylint),
        runner=run,
        environment=os.environ,
    )


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
