import argparse
import os
import sys
from pathlib import Path
from typing import Final, List, Mapping, Sequence

from bootstrap.layout import (
    BUILD_TOOLS,
    DEPLOYMENT_PACKAGE_PATH,
    DISTRIBUTION,
    DOCUMENTATION_FILES,
    DOCUMENTATION_PACKAGE_PATH,
    GPU_PACKAGES,
    INTERNAL_DIRECTORY,
    NOTICES,
    RELEASE_DEPLOYMENT,
    repository_root,
)
from bootstrap.platforms.factory import current_platform
from bootstrap.platforms.protocol import Platform
from bootstrap.processes import Runner, run
from bootstrap.project import read_project

VERSION_FLAG: Final[str] = "--version"


def missing_notices(bundle: Path) -> List[str]:
    """The license and notice files a release bundle ships that are absent from it."""
    return [name for name in NOTICES if not (bundle / name).is_file()]


def missing_documentation(bundle: Path) -> List[str]:
    """The files of the documentation site a bundle ships that are absent from its internals.

    The wheel the bundle is built from carries the site at the assets package's path, and the
    bundle unpacks its data under the same path, where Help > Documentation reads it.
    """
    site = bundle / INTERNAL_DIRECTORY / DOCUMENTATION_PACKAGE_PATH
    return [name for name in DOCUMENTATION_FILES if not (site / name).is_file()]


def carries_release_deployment(root: Path, bundle: Path) -> bool:
    """Whether a bundle carries the release deployment settings, as the wheel it was built from does.

    Args:
        root: The repository, which holds the release settings.
        bundle: The bundle's directory, beside its launcher.

    Returns:
        bool: Whether the bundle's deployment file matches the release settings byte for byte.
    """
    shipped = bundle / INTERNAL_DIRECTORY / DEPLOYMENT_PACKAGE_PATH
    return shipped.is_file() and shipped.read_bytes() == (root / RELEASE_DEPLOYMENT).read_bytes()


def carried_packages(bundle: Path, names: Sequence[str]) -> List[str]:
    """The packages among ``names`` found in a bundle, beside its launcher or among its internals."""
    directories = (bundle, bundle / INTERNAL_DIRECTORY)
    return [name for name in names if any((directory / name).is_dir() for directory in directories)]


def carried_build_tools(bundle: Path) -> List[str]:
    """The build-time packages found in a bundle, which the notices place on the build machine.

    A bundle carries the application and its runtime dependencies. Tooling that draws the assets
    belongs to the machine that builds it, so finding it here means the notices describe a
    different set of components than the bundle ships.
    """
    return carried_packages(bundle, BUILD_TOOLS)


def carried_gpu_packages(bundle: Path) -> List[str]:
    """The GPU packages found in a bundle, which the published bundles leave out.

    A release computes on the CPU, and GPU support is built locally. Finding CuPy or the CUDA
    wheels here means the release was built with a GPU extra.
    """
    return carried_packages(bundle, GPU_PACKAGES)


def bundle_failures(
    root: Path,
    platform: Platform,
    *,
    runner: Runner,
    environment: Mapping[str, str],
) -> List[str]:
    """What keeps the release bundle under ``root`` from shipping, each as a line of its own.

    The bundle ships its notices and its documentation, carries the release deployment settings,
    the application and its CPU runtime dependencies alone, and offers a launcher that starts.

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
    launcher = platform.bundling().launcher(root / DISTRIBUTION, name=name, directory=True)
    bundle = launcher.parent
    failures: List[str] = []
    absent = missing_notices(bundle)
    if absent:
        failures.append(f"Bundle {bundle} is missing {', '.join(absent)}")

    pages = missing_documentation(bundle)
    if pages:
        failures.append(f"Bundle {bundle} is missing its documentation: {', '.join(pages)}")

    if not carries_release_deployment(root, bundle):
        failures.append(f"Bundle {bundle} carries deployment settings other than {RELEASE_DEPLOYMENT}")

    carried = carried_build_tools(bundle)
    if carried:
        failures.append(f"Bundle {bundle} carries build-time tooling its notices leave out: {', '.join(carried)}")

    gpu = carried_gpu_packages(bundle)
    if gpu:
        failures.append(f"Bundle {bundle} carries GPU packages the published bundles leave out: {', '.join(gpu)}")

    if not launcher.is_file():
        failures.append(f"Bundle {bundle} offers no launcher at {launcher}")
        return failures

    status = runner((str(launcher), VERSION_FLAG), cwd=root, environment=environment, quiet=False)
    if status != 0:
        failures.append(f"Launcher {launcher} exited with status {status}")

    return failures


def main(argv: Sequence[str]) -> int:
    """Confirms the release bundle ships its notices, its documentation and the release deployment settings,
    holds to the notices, and that its launcher starts."""
    parser = argparse.ArgumentParser(description="Verify the release bundle before it is archived.")
    parser.parse_args(list(argv))

    failures = bundle_failures(repository_root(), current_platform(), runner=run, environment=os.environ)
    for failure in failures:
        print(f"::error::{failure}")

    if failures:
        return 1

    print("The bundle ships its notices, its documentation and the release settings, and its launcher starts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
