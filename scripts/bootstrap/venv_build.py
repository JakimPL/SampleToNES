import sys
from pathlib import Path
from typing import Dict, Final, Mapping, Sequence

from bootstrap.platforms.protocol import Platform
from bootstrap.processes import Runner, expect_success

BUILD_ENVIRONMENT: Final[str] = ".venv-build"
PIP_REQUIRE_VIRTUALENV: Final[str] = "PIP_REQUIRE_VIRTUALENV"


def build_environment(
    root: Path,
    *,
    runner: Runner,
    environment: Mapping[str, str],
) -> Path:
    """The virtual environment a bundle is built in, created under ``root`` where it is missing.

    Every package a build installs lands here, so the interpreter running the script stays as
    it was found.

    Args:
        root: The repository.
        runner: What runs the command creating the environment.
        environment: The variables the command sees.

    Returns:
        Path: The environment's directory.
    """
    directory = root / BUILD_ENVIRONMENT
    if directory.is_dir():
        print("Virtual environment already exists.")
        return directory

    print("Creating virtual environment...")
    expect_success(
        runner,
        (sys.executable, "-m", "venv", str(directory)),
        cwd=root,
        environment=environment,
    )
    print("Virtual environment created.")
    return directory


def install(
    root: Path,
    python: Path,
    *,
    extras: Sequence[str],
    runner: Runner,
    environment: Mapping[str, str],
) -> None:
    """Installs the package with ``extras`` into the environment ``python`` runs.

    Pip is told to refuse any interpreter outside a virtual environment, so an install reaches
    the build environment alone.

    Args:
        root: The repository, which is the package installed.
        python: The build environment's interpreter.
        extras: The optional-dependency extras installed with the package.
        runner: What runs the commands.
        environment: The variables the commands see.
    """
    guarded: Dict[str, str] = {**environment, PIP_REQUIRE_VIRTUALENV: "1"}
    print("Installing dependencies...")
    expect_success(
        runner,
        (str(python), "-m", "pip", "install", "--upgrade", "pip"),
        cwd=root,
        environment=guarded,
    )
    print(f"Installing with extras: {','.join(extras)}")
    expect_success(
        runner,
        (str(python), "-m", "pip", "install", f".[{','.join(extras)}]"),
        cwd=root,
        environment=guarded,
    )
    print("sampletones Python package installed successfully.")


def interpreter(
    root: Path,
    platform: Platform,
) -> Path:
    """The interpreter of the build environment under ``root``."""
    return platform.interpreter(root / BUILD_ENVIRONMENT)
