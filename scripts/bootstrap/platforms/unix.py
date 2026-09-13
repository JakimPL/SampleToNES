from pathlib import Path
from typing import Final, Tuple

UNIX_INTERPRETER: Final[Tuple[str, str]] = ("bin", "python")


def unix_interpreter(environment: Path) -> Path:
    """The interpreter a virtual environment at ``environment`` runs on Linux and macOS."""
    return environment.joinpath(*UNIX_INTERPRETER)
