import argparse
import os
import sys
from pathlib import Path
from typing import Final, List, Mapping, Sequence

from bootstrap.layout import BUILD_TOOLS, DISTRIBUTION, NOTICES, repository_root
from bootstrap.platforms.factory import current_platform
from bootstrap.platforms.protocol import Platform
from bootstrap.processes import Runner, run
from bootstrap.project import read_project

VERSION_FLAG: Final[str] = "--version"
INTERNAL_DIRECTORY: Final[str] = "_internal"


def missing_notices(bundle: Path) -> List[str]:
    """The license and notice files a release bundle ships that are absent from it."""
    return [name for name in NOTICES if not (bundle / name).is_file()]


def carried_build_tools(bundle: Path) -> List[str]:
    """The build-time packages found in a bundle, which the notices place on the build machine.

    A bundle carries the application and its runtime dependencies. Tooling that draws the assets
    belongs to the machine that builds it, so finding it here means the notices describe a
    different set of components than the bundle ships.
    """
    directories = (bundle, bundle / INTERNAL_DIRECTORY)
    return [name for name in BUILD_TOOLS if any((directory / name).is_dir() for directory in directories)]


def bundle_failures(
    root: Path,
    platform: Platform,
    *,
    runner: Runner,
    environment: Mapping[str, str],
) -> List[str]:
    """What keeps the release bundle under ``root`` from shipping, each as a line of its own.

    The bundle ships its notices, carries the application and its runtime dependencies alone, and
    offers a launcher that starts.

    Args:
        root: The repository the bundle was built in.
        platform: The system the bundle was built for.
        runner: What runs the launcher.
        environment: The variables the launcher sees.

    Returns:
        List[str]: The failures, empty for a bundle ready to archive.

    Raises:
        SystemExit: If the system builds no bundle.
    """
    name = read_project(root).name
    launcher = platform.bundling().launcher(root / DISTRIBUTION, name=name, release=True)
    bundle = launcher.parent
    failures: List[str] = []
    absent = missing_notices(bundle)
    if absent:
        failures.append(f"Bundle {bundle} is missing {', '.join(absent)}")

    carried = carried_build_tools(bundle)
    if carried:
        failures.append(f"Bundle {bundle} carries build-time tooling its notices leave out: {', '.join(carried)}")

    if not launcher.is_file():
        failures.append(f"Bundle {bundle} offers no launcher at {launcher}")
        return failures

    status = runner((str(launcher), VERSION_FLAG), cwd=root, environment=environment, quiet=False)
    if status != 0:
        failures.append(f"Launcher {launcher} exited with status {status}")

    return failures


def main(argv: Sequence[str]) -> int:
    """Confirms the release bundle ships its notices, holds to them, and that its launcher starts."""
    parser = argparse.ArgumentParser(description="Verify the release bundle before it is archived.")
    parser.parse_args(list(argv))

    failures = bundle_failures(repository_root(), current_platform(), runner=run, environment=os.environ)
    for failure in failures:
        print(f"::error::{failure}")

    if failures:
        return 1

    print("The bundle ships its notices and its launcher starts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
