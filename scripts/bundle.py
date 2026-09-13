import argparse
import os
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Final, List, Mapping, Sequence, Tuple

from bootstrap.interpreter import REQUIRED_VERSION, require_python
from bootstrap.platforms.factory import current_platform
from bootstrap.platforms.protocol import Platform
from bootstrap.preflight import check_build_interpreter
from bootstrap.processes import Runner, expect_success, run
from bootstrap.repository import repository_root
from bootstrap.venv_build import build_environment, install, interpreter

BUNDLE_NAME: Final[str] = "sampletones"
DISTRIBUTION: Final[str] = "bin"
ENTRY: Final[str] = "src/sampletones/__main__.py"
RELEASE_HOOK: Final[str] = "scripts/runtime_hooks/release_environment.py"
ICONS_SCRIPT: Final[str] = "scripts/assets/icons.py"
SELF_CHECK: Final[str] = "self-check"
BUILD_EXTRA: Final[str] = "build"
GPU_EXTRA: Final[str] = "gpu"
GROUPS: Final[Tuple[str, ...]] = ("assets",)
DATA: Final[Tuple[Tuple[str, str], ...]] = (
    ("src/sampletones_assets/icons", "assets/icons"),
    ("src/sampletones_assets/fonts", "assets/fonts"),
    ("src/sampletones_config", "config"),
    ("src/sampletones_player/driver/binary", "sampletones_player/driver/binary"),
)
DATA_SEPARATOR: Final[str] = ":"
EXCLUDED_MODULES: Final[Tuple[str, ...]] = ("PIL",)
NOTICES: Final[Tuple[str, ...]] = ("LICENSE", "THIRD-PARTY-NOTICES.md", "THIRD-PARTY-LICENSES.txt")
NO_BUNDLE: Final[str] = (
    "ERROR: a standalone bundle is built on Linux and Windows.\n"
    "On macOS, SampleToNES runs from source:\n"
    "\n"
    "    make system-deps\n"
    "    make setup\n"
    "    make run\n"
    "\n"
    "See docs/guide/installation.md for the full steps."
)


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
    platform: Platform,
    options: BundleOptions,
) -> List[str]:
    """The PyInstaller invocation that writes the bundle.

    Args:
        python: The build environment's interpreter.
        platform: The system the bundle is built for.
        options: How the bundle is built.

    Returns:
        List[str]: The command, run from the repository root.
    """
    command = [
        str(python),
        "-m",
        "PyInstaller",
        "--name",
        BUNDLE_NAME,
        "--onedir" if options.release else "--onefile",
        "--noconfirm",
        "--distpath",
        DISTRIBUTION,
        "--icon",
        platform.icon,
    ]
    for source, destination in DATA:
        command.extend(("--add-data", f"{source}{DATA_SEPARATOR}{destination}"))

    command.extend(("--copy-metadata", BUNDLE_NAME))
    for module in EXCLUDED_MODULES:
        command.extend(("--exclude-module", module))

    if options.release:
        command.extend(("--runtime-hook", RELEASE_HOOK))

    command.append(ENTRY)
    return command


def remove_previous(distribution: Path) -> None:
    """Removes what an earlier build left under ``distribution``, whichever shape it took."""
    for previous in (distribution / BUNDLE_NAME, distribution / f"{BUNDLE_NAME}.exe"):
        if previous.is_dir():
            print(f"Removing the previous artifact: {previous}")
            shutil.rmtree(previous)
        elif previous.exists():
            print(f"Removing the previous artifact: {previous}")
            previous.unlink()


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
        SystemExit: If a step fails, or PyInstaller produced no launcher.
    """
    if options.release:
        print("Release build: onedir bundle, injecting release deployment configuration")

    build_environment(root, runner=runner, environment=environment)
    python = interpreter(root, platform)
    install(
        root,
        python,
        extras=extras(options),
        groups=GROUPS,
        runner=runner,
        environment=environment,
    )
    check_build_interpreter(
        python,
        platform,
        release=options.release,
        runner=runner,
        cwd=root,
        environment=environment,
    )
    print("Generating the icon suite...")
    expect_success(runner, (str(python), ICONS_SCRIPT), cwd=root, environment=environment)

    distribution = root / DISTRIBUTION
    remove_previous(distribution)
    print("Building executable...")
    expect_success(
        runner,
        pyinstaller_command(python, platform, options),
        cwd=root,
        environment=environment,
    )
    launcher = platform.launcher(distribution, release=options.release)
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

    require_python(REQUIRED_VERSION)
    platform = current_platform()
    if not platform.bundles:
        print(NO_BUNDLE, file=sys.stderr)
        return 1

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
