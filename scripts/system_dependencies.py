import argparse
import os
import sys
from pathlib import Path
from typing import Mapping, Sequence

from bootstrap.layout import repository_root
from bootstrap.platforms.factory import current_platform
from bootstrap.platforms.protocol import Platform
from bootstrap.processes import Runner, expect_success, run


def install_system_packages(
    root: Path,
    platform: Platform,
    *,
    runner: Runner,
    environment: Mapping[str, str],
) -> int:
    """Installs the system packages building and running the application needs.

    Args:
        root: The repository, which the commands run in.
        platform: The system, which names its package manager and packages.
        runner: What runs the commands.
        environment: The variables the commands see.

    Returns:
        int: The exit status: 1 where the package manager is missing, 0 otherwise.

    Raises:
        SystemExit: If an install command fails.
    """
    missing = platform.missing_package_manager()
    if missing is not None:
        print(missing, file=sys.stderr)
        return 1

    commands = platform.system_packages()
    if not commands:
        print(f"Nothing to install on {platform.name}: the Python installer carries what the application needs.")
        return 0

    print("Installing system dependencies...")
    for command in commands:
        expect_success(runner, command, cwd=root, environment=environment)

    print("System dependencies installed.")
    return 0


def main(argv: Sequence[str]) -> int:
    """Installs the system packages building and running the application needs on this machine."""
    parser = argparse.ArgumentParser(description="Install the system packages SampleToNES needs.")
    parser.parse_args(list(argv))

    return install_system_packages(
        repository_root(),
        current_platform(),
        runner=run,
        environment=os.environ,
    )


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
