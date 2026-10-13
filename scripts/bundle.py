import argparse
import os
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Final, List, Mapping, Optional, Sequence, Tuple

from bootstrap.cuda import DEFAULT_GPU, GPU_CHOICES, gpu_extra
from bootstrap.files import remove_path
from bootstrap.interpreter import running_version
from bootstrap.layout import (
    BUILD_ENVIRONMENT,
    BUILD_TOOLS,
    CUDA_LIBRARY_DIRECTORIES,
    CUDA_PACKAGE,
    CUPY_PACKAGES,
    DISTRIBUTION,
    GPU_HOOK,
    GPU_PACKAGES,
    INTERNAL_DIRECTORY,
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
GPU_FLAG: Final[str] = "--gpu"
DOCUMENTATION_FLAG: Final[str] = "--documentation"
CPU_BUILD_ADVICE: Final[str] = "Build with '--gpu 0' for the CPU alone."


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


def cuda_library_directories(site_packages: Path) -> List[Path]:
    """The directories the CUDA wheels installed in ``site_packages`` keep their shared libraries in.

    Args:
        site_packages: The site-packages directory of the environment the bundle is built in.

    Returns:
        List[Path]: The directories, in name order, empty where the CUDA wheels are absent.
    """
    root = site_packages / CUDA_PACKAGE
    if not root.is_dir():
        return []

    return sorted(
        component / libraries
        for component in root.iterdir()
        for libraries in CUDA_LIBRARY_DIRECTORIES
        if (component / libraries).is_dir()
    )


def leading_search_path(
    environment: Mapping[str, str],
    *,
    variable: str,
    directories: Sequence[Path],
) -> Dict[str, str]:
    """The variables ``environment`` holds, with ``directories`` leading the search path ``variable`` names.

    Args:
        environment: The variables to extend.
        variable: The search path's variable.
        directories: The directories searched first, in order.

    Returns:
        Dict[str, str]: The variables, the search path keeping its earlier entries after ``directories``.
    """
    entries = [str(directory) for directory in directories]
    existing = environment.get(variable)
    if existing:
        entries.append(existing)

    return {**environment, variable: os.pathsep.join(entries)}


def pyinstaller_environment(
    root: Path,
    platform: Platform,
    options: BundleOptions,
    environment: Mapping[str, str],
) -> Dict[str, str]:
    """The variables PyInstaller runs under.

    CuPy names the CUDA libraries it links by their file names alone, and PyInstaller looks each
    name up the way the system loader does. A GPU build places the CUDA wheels' library directories
    first on that search, so every name resolves to the wheel the bundle carries, ahead of a CUDA
    toolkit installed on the build machine, whose copy would land at the top of the bundle.

    Args:
        root: The repository, which holds the build environment.
        platform: The system the bundle is built on, which places the search path and the packages.
        options: How the bundle is built.
        environment: The variables the build was started with.

    Returns:
        Dict[str, str]: The variables, as given for a CPU build.
    """
    if not options.gpu:
        return dict(environment)

    site_packages = platform.site_packages(root / BUILD_ENVIRONMENT)
    return leading_search_path(
        environment,
        variable=platform.bundling().library_search_variable,
        directories=cuda_library_directories(site_packages),
    )


def stray_cuda_libraries(bundle: Path) -> List[str]:
    """The libraries at the top of a bundle's internals that repeat one the CUDA wheels carry.

    Args:
        bundle: The bundle's directory, beside its launcher.

    Returns:
        List[str]: The repeated file names, in name order, empty for a bundle carrying each CUDA library once.
    """
    internal = bundle / INTERNAL_DIRECTORY
    carried = {path.name for path in (internal / CUDA_PACKAGE).rglob("*") if path.is_file()}
    return sorted(path.name for path in internal.iterdir() if path.name in carried)


def check_cuda_libraries(bundle: Path) -> None:
    """Holds a GPU bundle to carrying each CUDA library once, the copy its wheel brings.

    Args:
        bundle: The bundle's directory, beside its launcher.

    Raises:
        SystemExit: If a library sits at the top of the bundle beside the wheel's copy.
    """
    stray = stray_cuda_libraries(bundle)
    if stray:
        raise SystemExit(
            f"Build failed: {bundle} carries a second copy of CUDA libraries its wheels bring: "
            f"{', '.join(stray)}. {CPU_BUILD_ADVICE}"
        )


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


def self_check_command(launcher: Path, options: BundleOptions) -> Tuple[str, ...]:
    """The launcher's self-check, held to the documentation the wheel carries, which a GPU bundle runs
    with the GPU check that proves it computes on the card."""
    if options.gpu:
        return (str(launcher), SELF_CHECK, DOCUMENTATION_FLAG, GPU_FLAG)

    return (str(launcher), SELF_CHECK, DOCUMENTATION_FLAG)


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
        SystemExit: If the system builds no bundle, a step fails, PyInstaller produced no launcher, or a
            GPU bundle carries a CUDA library twice.
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
        environment=pyinstaller_environment(root, platform, options, environment),
    )
    launcher = bundling.launcher(distribution, name=project.name, directory=options.directory)
    if not launcher.is_file():
        raise SystemExit(f"Build failed: PyInstaller produced no executable at {launcher}.")

    if options.gpu:
        check_cuda_libraries(launcher.parent)

    print("Verifying the bundle...")
    status = runner(self_check_command(launcher, options), cwd=root, environment=environment, quiet=False)
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
