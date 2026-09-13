import argparse
import os
import sys
from typing import Final, Sequence, Tuple

from bootstrap.processes import expect_success, run
from bootstrap.repository import repository_root

INSTALL_HOOKS: Final[Tuple[str, ...]] = (
    "uv",
    "run",
    "pre-commit",
    "install",
    "--hook-type",
    "pre-commit",
    "--hook-type",
    "pre-push",
)


def main(argv: Sequence[str]) -> int:
    """Installs the git hooks pre-commit runs at commit and at push."""
    parser = argparse.ArgumentParser(description="Install the pre-commit hooks.")
    parser.parse_args(list(argv))

    print("Installing pre-commit hooks...")
    expect_success(run, INSTALL_HOOKS, cwd=repository_root(), environment=os.environ)
    print("Pre-commit hooks installed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
