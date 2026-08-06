import os
import shutil
from pathlib import Path
from typing import Optional

from tests.integration.paths import REPO_ROOT


def resolve_output_directory(variable: str) -> Optional[Path]:
    """Reads the persistent output directory an environment variable names.

    Emission is opt-in so an ordinary (and parallel) run writes only to ``tmp_path``.
    A named directory is cleaned once per session, so each run leaves a fresh set of
    files there.

    Args:
        variable: Environment variable naming the directory.

    Returns:
        Optional[Path]: The prepared directory, or ``None`` while emission is unasked for.
    """
    configured = os.environ.get(variable)
    if not configured:
        return None

    directory = Path(configured)
    if not directory.is_absolute():
        directory = REPO_ROOT / directory

    if directory.exists():
        shutil.rmtree(directory)

    directory.mkdir(parents=True, exist_ok=True)
    return directory


def resolve_output_path(output_directory: Optional[Path], tmp_path: Path, filename: str) -> Path:
    """Locates a produced file: the persistent directory where one is named, else ``tmp_path``.

    Args:
        output_directory: The persistent directory, or ``None`` while emission is unasked for.
        tmp_path: The test's own temporary directory.
        filename: Name the produced file carries.

    Returns:
        Path: Where the file is written.
    """
    base = output_directory if output_directory is not None else tmp_path
    return base / filename
