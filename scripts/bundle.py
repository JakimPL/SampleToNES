import argparse
import os
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Final, List, Mapping, Sequence, Tuple

from bootstrap.files import remove_path
from bootstrap.interpreter import running_version
from bootstrap.layout import BUILD_TOOLS, DISTRIBUTION, NOTICES, RELEASE_HOOK, repository_root
from bootstrap.platforms.bundling import Bundling
from bootstrap.platforms.factory import current_platform
from bootstrap.platforms.protocol import Platform
from bootstrap.preflight import check_build_interpreter
from bootstrap.processes import Runner, expect_success, run
from bootstrap.project import BUILD_EXTRA, GPU_EXTRA, Project, read_project
from bootstrap.venv_build import ensure_build_venv, install

SELF_CHECK: Final[str] = "self-check"


@dataclass(frozen=True)
class BundleOptions:
    """How a bundle is built.

    Attributes:
        release: Whether the bundle is a release: a directory beside its launcher, carrying the
            release deployment configuration and the notices.
        gpu: Whether the bundle carries GPU support.
    """

    release: bool
    gpu: bool


def extras(options: BundleOptions) -> Tuple[str, ...]:
    """The optional-dependency extras a bundle is built with."""
    if options.gpu:
        return (BUILD_EXTRA, GPU_EXTRA)

    return (BUILD_EXTRA,)


def pyinstaller_command(
    python: Path,
    bundling: Bundling,
    project: Project,
    options: BundleOptions,
) -> List[str]:
    """The PyInstaller invocation that writes the bundle.

    Every package the wheel carries brings its data files along at its own package path, so the
    frozen application reads them through ``importlib.resources`` the way an installed one does.

    Args:
        python: The build environment's interpreter.
        bundling: What building a bundle takes on the system.
        project: The project the bundle is built from.
        options: How the bundle is built.

    Returns:
        List[str]: The command, run from the repository root.
    """
    command = [
        str(python),
        "-m",
        "PyInstaller",
        "--name",
        project.name,
        "--onedir" if options.release else "--onefile",
        "--noconfirm",
        "--distpath",
        DISTRIBUTION,
        "--icon",
        bundling.icon,
    ]
    for package in project.packages:
        command.extend(("--collect-data", package))

    command.extend(("--copy-metadata", project.name))
    for module in BUILD_TOOLS:
        command.extend(("--exclude-module", module))

    if options.release:
        command.extend(("--runtime-hook", RELEASE_HOOK))

    command.append(project.entry_script)
    return command


def remove_previous(distribution: Path, bundling: Bundling, name: str) -> None:
    """Removes what an earlier build left under ``distribution``, a release's directory or a single file."""
    for previous in (
        bundling.launcher(distribution, name=name, release=True).parent,
        bundling.launcher(distribution, name=name, release=False),
    ):
        if remove_path(previous):
            print(f"Removed the previous artifact: {previous}")


def copy_notices(root: Path, bundle: Path) -> None:
    """Places the license and notice files beside a release bundle's launcher."""
    for notice in NOTICES:
        shutil.copyfile(root / notice, bundle / notice)

    print(f"Bundled notices: {', '.join(NOTICES)}")


def build_bundle(
    root: Path,
    platform: Platform,
    options: BundleOptions,
    *,
    runner: Runner,
    environment: Mapping[str, str],
) -> Path:
    """Builds the standalone bundle in a build environment of its own and verifies it starts.

    Args:
        root: The repository.
        platform: The system the bundle is built on and for.
        options: How the bundle is built.
        runner: What runs the commands.
        environment: The variables the commands see.

    Returns:
        Path: The launcher the bundle offers.

    Raises:
        SystemExit: If the system builds no bundle, a step fails, or PyInstaller produced no launcher.
    """
    bundling = platform.bundling()
    project = read_project(root)
    if options.release:
        print("Release build: onedir bundle, injecting release deployment configuration")

    python = ensure_build_venv(
        root,
        platform,
        runner=runner,
        environment=environment,
    )
    install(
        root,
        python,
        extras=extras(options),
        runner=runner,
        environment=environment,
    )
    check_build_interpreter(
        python,
        bundling,
        release=options.release,
        runner=runner,
        cwd=root,
        environment=environment,
    )
    distribution = root / DISTRIBUTION
    remove_previous(distribution, bundling, project.name)
    print("Building executable...")
    expect_success(
        runner,
        pyinstaller_command(python, bundling, project, options),
        cwd=root,
        environment=environment,
    )
    launcher = bundling.launcher(distribution, name=project.name, release=options.release)
    if not launcher.is_file():
        raise SystemExit(f"Build failed: PyInstaller produced no executable at {launcher}.")

    print("Verifying the bundle...")
    status = runner((str(launcher), SELF_CHECK), cwd=root, environment=environment, quiet=False)
    if status != 0:
        raise SystemExit(f"Build failed: {launcher} did not pass its self-check.")

    if options.release:
        copy_notices(root, launcher.parent)

    print(f"Build complete: {launcher}")
    return launcher


def main(argv: Sequence[str]) -> int:
    """Builds the standalone bundle, as a development build or a release."""
    parser = argparse.ArgumentParser(description="Build the standalone SampleToNES bundle.")
    parser.add_argument(
        "--release",
        action="store_true",
        help="build a release: a directory bundle with the release deployment configuration and the notices",
    )
    parser.add_argument(
        "--gpu",
        action="store_true",
        help="build with GPU support",
    )
    arguments = parser.parse_args(list(argv))
    options = BundleOptions(release=arguments.release, gpu=arguments.gpu)

    print(f"Detected Python version: {running_version()}")
    build_bundle(
        repository_root(),
        current_platform(),
        options,
        runner=run,
        environment=os.environ,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
