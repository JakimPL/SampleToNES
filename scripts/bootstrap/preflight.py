from pathlib import Path
from typing import Final, Mapping

from bootstrap.platforms.protocol import Platform
from bootstrap.processes import Runner

PYAUDIO: Final[str] = "pyaudio"
TKINTER: Final[str] = "tkinter"


def can_import(
    python: Path,
    module: str,
    *,
    runner: Runner,
    cwd: Path,
    environment: Mapping[str, str],
) -> bool:
    """Whether the interpreter at ``python`` imports ``module``.

    Args:
        python: The interpreter.
        module: The module's name.
        runner: What runs the probe.
        cwd: The directory the probe runs in.
        environment: The variables the probe sees.

    Returns:
        bool: Whether the import succeeds.
    """
    status = runner(
        (str(python), "-c", f"import {module}"),
        cwd=cwd,
        environment=environment,
        quiet=True,
    )
    return status == 0


def check_build_interpreter(
    python: Path,
    platform: Platform,
    *,
    release: bool,
    runner: Runner,
    cwd: Path,
    environment: Mapping[str, str],
) -> None:
    """Holds the build interpreter to what a bundle has to carry.

    Audio playback is required of every bundle. Tk is required of a release bundle, so the
    shipped executable opens file dialogs on its own; a development bundle built without it is
    warned about what it leans on instead.

    Args:
        python: The build environment's interpreter.
        platform: The system the build runs on.
        release: Whether the bundle is a release.
        runner: What runs the probes.
        cwd: The directory the probes run in.
        environment: The variables the probes see.

    Raises:
        SystemExit: If the interpreter cannot play audio, or a release lacks Tk.
    """
    print("Checking the build environment...")
    if not can_import(python, PYAUDIO, runner=runner, cwd=cwd, environment=environment):
        raise SystemExit(
            "ERROR: the build interpreter cannot import pyaudio, so the bundle would carry no audio playback.\n"
            f"{platform.pyaudio_advice}"
        )

    print(f"{PYAUDIO}: available")
    if can_import(python, TKINTER, runner=runner, cwd=cwd, environment=environment):
        print(f"{TKINTER}: available")
        return

    if release:
        raise SystemExit(
            "ERROR: the build interpreter cannot import tkinter, so a release bundle would depend on the "
            f"machine running it for file dialogs.\n{platform.tkinter_advice}"
        )

    print(f"WARNING: the build interpreter cannot import tkinter. {platform.tkinter_warning}")
