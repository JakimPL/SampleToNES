from pathlib import Path
from typing import Dict, Final

from sampletones_core.compatibility.kind import ObjectKind
from sampletones_shared.paths.extensions import (
    EXT_FILE_LIBRARY,
    EXT_FILE_PROJECT,
    EXT_FILE_RECONSTRUCTION,
)
from sampletones_shared.paths.source import REPOSITORY_ROOT

CORPUS_DIRECTORY: Final[Path] = REPOSITORY_ROOT / "tests" / "data" / "compatibility"
CORPUS_EXTENSIONS: Final[Dict[ObjectKind, str]] = {
    ObjectKind.RECONSTRUCTION: EXT_FILE_RECONSTRUCTION,
    ObjectKind.LIBRARY: EXT_FILE_LIBRARY,
    ObjectKind.PROJECT: EXT_FILE_PROJECT,
}


def version_part(version: str) -> str:
    """The spelling a data version takes in a file name.

    A step module is named after the version it writes, so an archived file named after the
    version it was written at reads as the step's counterpart: ``v2_1.stn`` is what ``v2_2.py``
    carries forward.
    """
    return f"v{version.replace('.', '_')}"


def archived_path(kind: ObjectKind, version: str, root: Path = CORPUS_DIRECTORY) -> Path:
    """Where the file one format wrote at ``version`` is kept.

    Args:
        kind: The format the file belongs to.
        version: The data version the file was written at.
        root: The corpus the file is kept in.

    Returns:
        Path: The archived file's location, whether or not it stands there yet.
    """
    return root / kind.value / f"{version_part(version)}{CORPUS_EXTENSIONS[kind]}"
