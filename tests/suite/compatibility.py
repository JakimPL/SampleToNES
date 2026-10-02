import io
import json
import zipfile
from pathlib import Path
from typing import Any, Dict, Final, Optional

import msgpack

from sampletones_core.compatibility.kind import ObjectKind
from sampletones_core.data.document import decompress_document
from sampletones_tools.compatibility.paths import CORPUS_DIRECTORY, archived_path

RECONSTRUCTION_VERSION: Final[str] = "2.1"
LIBRARY_VERSION: Final[str] = "2.0"
PROJECT_VERSION: Final[str] = "1.0"
WRITING_RELEASE: Final[str] = "0.3.1"
PROJECT_DOCUMENT: Final[str] = "project.json"
FORMAT_VERSION_FIELD: Final[str] = "format_version"
METADATA_FIELD: Final[str] = "metadata"
VERSION_FIELD: Final[str] = "version"

ARCHIVED_VERSIONS: Final[Dict[ObjectKind, str]] = {
    ObjectKind.RECONSTRUCTION: RECONSTRUCTION_VERSION,
    ObjectKind.LIBRARY: LIBRARY_VERSION,
    ObjectKind.PROJECT: PROJECT_VERSION,
}


def archived(kind: ObjectKind, version: str) -> Path:
    """The archived file one format wrote at ``version``, which the corpus keeps."""
    return archived_path(kind, version, CORPUS_DIRECTORY)


def stored_document(path: Path) -> Dict[str, Any]:
    """What one stored file holds, read without a model so the version can be read first.

    A project keeps its document inside an archive, while a reconstruction and a library are the
    payload itself, deflated by the builds that frame their documents, so this answers with the
    mapping whichever of these the file is.
    """
    if path.suffix == ".stp":
        with zipfile.ZipFile(path) as archive:
            document: Dict[str, Any] = json.loads(archive.read(PROJECT_DOCUMENT))
            return document

    payload: Dict[str, Any] = msgpack.unpackb(decompress_document(path.read_bytes()), raw=False)
    return payload


def stored_version(kind: ObjectKind, path: Path) -> Optional[str]:
    """The data version an archived file states, read off the stored payload."""
    document = stored_document(path)
    if kind is ObjectKind.PROJECT:
        version = document.get(FORMAT_VERSION_FIELD)
    else:
        metadata = document.get(METADATA_FIELD, {})
        version = metadata.get(f"{kind.value}_data_version")

    return version if isinstance(version, str) else None


def writing_release(path: Path) -> Optional[str]:
    """The release that wrote an archived file, which every stored document names."""
    document = stored_document(path)
    metadata = document.get(METADATA_FIELD, {})
    release = metadata.get(VERSION_FIELD)
    return release if isinstance(release, str) else None


def restated_document(path: Path, kind: ObjectKind, version: str) -> bytes:
    """The bytes of the archived file at ``path`` with its stored data version replaced by ``version``.

    Everything else stays as the writing build left it, so a load refusing the result refuses it
    for its version alone.
    """
    document = stored_document(path)
    if kind is ObjectKind.PROJECT:
        document[FORMAT_VERSION_FIELD] = version
        return _rearchived(path, json.dumps(document).encode())

    document[METADATA_FIELD][f"{kind.value}_data_version"] = version
    packed: bytes = msgpack.packb(document, use_bin_type=True)
    return packed


def _rearchived(path: Path, project_document: bytes) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(path) as source, zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as target:
        for member in source.infolist():
            content = project_document if member.filename == PROJECT_DOCUMENT else source.read(member)
            target.writestr(member, content)

    return buffer.getvalue()
