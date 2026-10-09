import argparse
import os
import sys
from pathlib import Path
from typing import Final, Mapping, Sequence, Tuple

from bootstrap.layout import repository_root
from bootstrap.processes import Runner, expect_success, run

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


def install_hooks(
    root: Path,
    *,
    runner: Runner,
    environment: Mapping[str, str],
) -> None:
    """Installs the git hooks pre-commit runs at commit and at push.

    Raises:
        SystemExit: If pre-commit fails to install them.
    """
    print("Installing pre-commit hooks...")
    expect_success(runner, INSTALL_HOOKS, cwd=root, environment=environment)
    print("Pre-commit hooks installed.")


def main(argv: Sequence[str]) -> int:
    """Installs the git hooks pre-commit runs at commit and at push."""
    parser = argparse.ArgumentParser(description="Install the pre-commit hooks.")
    parser.parse_args(list(argv))

    install_hooks(repository_root(), runner=run, environment=os.environ)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
