import os
import shutil
import sys
from pathlib import Path
from typing import Dict, Final, Mapping, Optional

from .system import System

LIBRARY_PATH: Final[str] = "LD_LIBRARY_PATH"
ORIGINAL_LIBRARY_PATH: Final[str] = "LD_LIBRARY_PATH_ORIG"


def locate_program(program: str) -> Optional[Path]:
    """Where a program is installed, found the way a shell finds it.

    Args:
        program: The program's name, as it answers on the command line.

    Returns:
        Optional[Path]: The program's location, and None where this system carries none.
    """
    located = shutil.which(program)
    if located is None:
        return None

    return Path(located)


def missing_program_message(
    program: str,
    purpose: str,
    hints: Mapping[System, str],
) -> str:
    """What to report when a program the project reaches for is absent.

    Each supported system states its own way of installing the program, so the message names the
    command this one is served by.

    Args:
        program: The program's name, as it answers on the command line.
        purpose: What the project runs the program for.
        hints: How each supported system installs it.

    Returns:
        str: The message, naming the program, what it is for and how this system installs it.

    Raises:
        OSError: If the system is unsupported.
        KeyError: If no hint is stated for this system.
    """
    return f"{program} is missing: {purpose} ({hints[System.current()]})"


def running_frozen() -> bool:
    """Whether the application runs from a PyInstaller bundle, which marks ``sys`` as frozen."""
    return bool(getattr(sys, "frozen", False))


def reader_environment(
    environment: Mapping[str, str],
    *,
    frozen: bool,
) -> Dict[str, str]:
    """The variables ``environment`` holds, with the library path the reader's own session set.

    A PyInstaller bundle points ``LD_LIBRARY_PATH`` at the libraries it carries and keeps the
    reader's own value in ``LD_LIBRARY_PATH_ORIG``. A frozen run therefore answers the reader's
    value, or no library path where the reader set none, and any other run answers ``environment``
    as it stands.
    """
    variables = dict(environment)
    if not frozen:
        return variables

    original = variables.pop(ORIGINAL_LIBRARY_PATH, None)
    if original is None:
        variables.pop(LIBRARY_PATH, None)
    else:
        variables[LIBRARY_PATH] = original

    return variables


def program_environment() -> Dict[str, str]:
    """The variables a program of the system starts with: this process's, with the reader's library path.

    A file manager, a browser or a dialog tool started with them loads the system's libraries, in a
    bundle as in an installed copy.
    """
    return reader_environment(os.environ, frozen=running_frozen())
