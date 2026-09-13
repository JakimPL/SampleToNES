import argparse
import os
import sys
from typing import Sequence

from bootstrap.platforms.factory import current_platform
from bootstrap.processes import expect_success, run
from bootstrap.repository import repository_root


def main(argv: Sequence[str]) -> int:
    """Installs the system packages building and running the application needs on this machine."""
    parser = argparse.ArgumentParser(description="Install the system packages SampleToNES needs.")
    parser.parse_args(list(argv))

    platform = current_platform()
    missing = platform.missing_package_manager()
    if missing is not None:
        print(missing, file=sys.stderr)
        return 1

    commands = platform.system_packages()
    if not commands:
        print(f"Nothing to install on {platform.name}: the Python installer carries what the application needs.")
        return 0

    root = repository_root()
    print("Installing system dependencies...")
    for command in commands:
        expect_success(run, command, cwd=root, environment=os.environ)

    print("System dependencies installed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
