from pathlib import Path
from typing import Final, Tuple

UNIX_INTERPRETER: Final[Tuple[str, str]] = ("bin", "python")
UNIX_SITE_PACKAGES: Final[str] = "lib/python3.*/site-packages"


def unix_interpreter(environment: Path) -> Path:
    """The interpreter a virtual environment at ``environment`` runs on Linux and macOS."""
    return environment.joinpath(*UNIX_INTERPRETER)


def unix_site_packages(environment: Path) -> Path:
    """The directory a virtual environment at ``environment`` installs packages into on Linux and macOS.

    The directory is named after the version of the interpreter that created the environment, so
    it is found among the directories the environment holds.

    Raises:
        FileNotFoundError: If the environment holds no such directory, or several.
    """
    found = sorted(environment.glob(UNIX_SITE_PACKAGES))
    if len(found) != 1:
        raise FileNotFoundError(f"Expected one site-packages directory in {environment}, found {len(found)}")

    return found[0]
