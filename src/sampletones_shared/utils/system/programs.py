import shutil
from pathlib import Path
from typing import Mapping, Optional

from .system import System


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
