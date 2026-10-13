import argparse
import sys
import zipfile
from pathlib import Path
from typing import Final, List, Sequence

from bootstrap.layout import DEPLOYMENT_PACKAGE_PATH, RELEASE_DEPLOYMENT, WHEELS, repository_root

WHEEL_PATTERN: Final[str] = "*.whl"


def deployment_entries(wheel: Path) -> List[bytes]:
    """Every copy of the deployment settings a wheel carries, in archive order."""
    with zipfile.ZipFile(wheel) as archive:
        return [archive.read(entry) for entry in archive.infolist() if entry.filename == DEPLOYMENT_PACKAGE_PATH]


def wheel_failures(root: Path) -> List[str]:
    """What keeps the wheels built under ``root`` from publishing, each as a line of its own.

    Every wheel carries the release deployment settings once, as the wheel build writes them, so an
    installed package is quiet and self-healing.

    Args:
        root: The repository the wheels were built in.

    Returns:
        List[str]: The failures, empty for wheels ready to publish.
    """
    directory = root / WHEELS
    wheels = sorted(directory.glob(WHEEL_PATTERN))
    if not wheels:
        return [f"No wheel found in {directory}"]

    release = (root / RELEASE_DEPLOYMENT).read_bytes()
    failures: List[str] = []
    for wheel in wheels:
        entries = deployment_entries(wheel)
        if len(entries) != 1:
            failures.append(f"Wheel {wheel.name} carries {len(entries)} copies of {DEPLOYMENT_PACKAGE_PATH}")
        elif entries[0] != release:
            failures.append(f"Wheel {wheel.name} carries deployment settings other than {RELEASE_DEPLOYMENT}")

    return failures


def main(argv: Sequence[str]) -> int:
    """Confirms every built wheel carries the release deployment settings."""
    parser = argparse.ArgumentParser(description="Verify the built wheels before they are published.")
    parser.parse_args(list(argv))

    failures = wheel_failures(repository_root())
    for failure in failures:
        print(f"::error::{failure}")

    if failures:
        return 1

    print("Every wheel carries the release deployment settings")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
