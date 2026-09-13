import argparse
import os
import sys
from typing import Final, Sequence, Set, Tuple

from bootstrap.passes import Pass, run_passes
from bootstrap.processes import run
from bootstrap.repository import repository_root

MYPY: Final[str] = "mypy"
PYLINT: Final[str] = "pylint"
LINTED_TREES: Final[Tuple[str, ...]] = ("src", "scripts")


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


def main(argv: Sequence[str]) -> int:
    """Type checks and lints the code, and reports which linter failed."""
    parser = argparse.ArgumentParser(description="Type check and lint the SampleToNES code.")
    parser.add_argument("--mypy", action="store_true", help="run mypy alone")
    parser.add_argument("--pylint", action="store_true", help="run pylint alone")
    parser.add_argument("paths", nargs="*", help="files or directories to lint in place of the whole trees")
    arguments = parser.parse_args(list(argv))

    chosen: Set[str] = {name for name, wanted in ((MYPY, arguments.mypy), (PYLINT, arguments.pylint)) if wanted}
    passes = tuple(linter for linter in linters(tuple(arguments.paths)) if not chosen or linter.name in chosen)
    failed = run_passes(passes, root=repository_root(), runner=run, environment=os.environ)
    if failed:
        print(f"Linting failed: {', '.join(failed)}.")
        return 1

    print("All linting checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
