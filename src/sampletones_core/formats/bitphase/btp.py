import gzip
import json
from pathlib import Path
from typing import Final, Tuple

from sampletones_core.formats.bitphase.model.project import BitphaseProject

JSON_SEPARATORS: Final[Tuple[str, str]] = (",", ":")
FIXED_TIMESTAMP: Final[int] = 0


def project_to_bytes(project: BitphaseProject) -> bytes:
    """Serializes a document the way Bitphase reads it back.

    A ``.btp`` is the document's JSON under gzip, written without separator padding
    and with a fixed timestamp, so exporting the same document twice yields the same
    bytes.

    Args:
        project: The document to serialize.

    Returns:
        bytes: The file's contents.
    """
    payload = json.dumps(
        project.model_dump(mode="json", by_alias=True),
        separators=JSON_SEPARATORS,
    )
    return gzip.compress(payload.encode("utf-8"), mtime=FIXED_TIMESTAMP)


def write_btp(destination: Path, project: BitphaseProject) -> None:
    """Writes a Bitphase document to disk.

    Args:
        destination: The file to write.
        project: The document to serialize.

    Raises:
        OSError: If the destination cannot be written.
    """
    destination.write_bytes(project_to_bytes(project))
