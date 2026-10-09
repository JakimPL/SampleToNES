import argparse
import os
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Final, List, Mapping, Optional, Sequence, Tuple

from bootstrap.cuda import DEFAULT_GPU, GPU_CHOICES, gpu_extra
from bootstrap.files import remove_path
from bootstrap.interpreter import running_version
from bootstrap.layout import (
    BUILD_TOOLS,
    CUPY_PACKAGES,
    DISTRIBUTION,
    GPU_HOOK,
    GPU_PACKAGES,
    NOTICES,
    PYINSTALLER_HOOKS,
    RELEASE_HOOK,
    repository_root,
)
from bootstrap.platforms.bundling import Bundling
from bootstrap.platforms.factory import current_platform
from bootstrap.platforms.protocol import Platform
from bootstrap.preflight import check_build_interpreter
from bootstrap.processes import Runner, expect_success, run
from bootstrap.project import BUILD_EXTRA, Project, read_project
from bootstrap.venv_build import ensure_build_venv, install

SELF_CHECK: Final[str] = "self-check"


@dataclass(frozen=True)
class BundleOptions:
    """How a bundle is built.

    Attributes:
        release: Whether the bundle is a release: carrying the release deployment configuration
            and the notices.
        gpu_extra: The optional-dependency extra bringing GPU support, or ``None`` for a bundle
            computing on the CPU.
    """

    release: bool
    gpu_extra: Optional[str]

    @property
    def gpu(self) -> bool:
        """Whether the bundle carries GPU support."""
        return self.gpu_extra is not None

    @property
    def directory(self) -> bool:
        """Whether the bundle is a directory beside its launcher.

        A release is one so its notices sit beside the launcher. A GPU bundle is one because the
        CUDA libraries it carries weigh gigabytes, which a single file would unpack on every start.
        """
        return self.release or self.gpu


def extras(options: BundleOptions) -> Tuple[str, ...]:
    """The optional-dependency extras a bundle is built with."""
    if options.gpu_extra is not None:
        return (BUILD_EXTRA, options.gpu_extra)

    return (BUILD_EXTRA,)


def backend_arguments(options: BundleOptions) -> List[str]:
    """The PyInstaller arguments shaping what the bundle computes on.

    A CPU bundle leaves the GPU packages out, so a build environment that carried them for an
    earlier GPU build ships nothing of them. A GPU bundle collects CuPy whole, since it imports its
    modules dynamically, and brings the CUDA wheels in through the repository's own hooks.
    """
    if options.gpu_extra is None:
        arguments: List[str] = []
        for package in GPU_PACKAGES:
            arguments.extend(("--exclude-module", package))

        return arguments

    arguments = ["--additional-hooks-dir", PYINSTALLER_HOOKS, "--runtime-hook", GPU_HOOK]
    for package in CUPY_PACKAGES:
        arguments.extend(("--collect-all", package))

    return arguments


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
        "--onedir" if options.directory else "--onefile",
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

    command.extend(backend_arguments(options))
    if options.release:
        command.extend(("--runtime-hook", RELEASE_HOOK))

    command.append(project.entry_script)
    return command


def remove_previous(distribution: Path, bundling: Bundling, name: str) -> None:
    """Removes what an earlier build left under ``distribution``, a bundle's directory or a single file."""
    for previous in (
        bundling.launcher(distribution, name=name, directory=True).parent,
        bundling.launcher(distribution, name=name, directory=False),
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

    if options.gpu_extra is not None:
        print(f"GPU build: onedir bundle carrying the '{options.gpu_extra}' extra")

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
        gpu=options.gpu,
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
    launcher = bundling.launcher(distribution, name=project.name, directory=options.directory)
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
    """Builds the standalone bundle, as a development build or a release, with GPU support where a driver is found."""
    parser = argparse.ArgumentParser(description="Build the standalone SampleToNES bundle.")
    parser.add_argument(
        "--release",
        action="store_true",
        help="build a release: a directory bundle with the release deployment configuration and the notices",
    )
    parser.add_argument(
        "--gpu",
        default=DEFAULT_GPU,
        choices=GPU_CHOICES,
        help="auto to match the NVIDIA driver, 0 for the CPU backend, or the GPU extra to bundle",
    )
    arguments = parser.parse_args(list(argv))
    platform = current_platform()
    options = BundleOptions(
        release=arguments.release,
        gpu_extra=gpu_extra(arguments.gpu, platform, os.environ),
    )

    print(f"Detected Python version: {running_version()}")
    build_bundle(
        repository_root(),
        platform,
        options,
        runner=run,
        environment=os.environ,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
