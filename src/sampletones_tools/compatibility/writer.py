from pathlib import Path
from typing import List

from sampletones_core.compatibility.kind import ObjectKind
from sampletones_core.compatibility.upgrade import CURRENT_VERSIONS
from sampletones_core.project.container import ProjectContainer
from sampletones_tools.compatibility.documents import (
    corpus_instructions,
    corpus_library,
    corpus_project,
    corpus_reconstruction,
    embedded_reconstruction,
)
from sampletones_tools.compatibility.paths import CORPUS_DIRECTORY, archived_path


def archive(root: Path = CORPUS_DIRECTORY, force: bool = False) -> List[Path]:
    """Writes one document per format at the version this build states, and answers where they went.

    Each file is written by the build that runs this, so the corpus holds what a release actually
    produced rather than what a later build believes it produced. A version already archived stands
    as it was written, since replacing it would restate history under the same name; ``force`` is
    what a deliberate replacement passes.

    Args:
        root: The corpus the files are written into.
        force: Whether a version already archived is written again.

    Returns:
        List[Path]: The files written, in the order the formats are listed.
    """
    written: List[Path] = []
    for kind, version in CURRENT_VERSIONS.items():
        path = archived_path(kind, version, root)
        if path.exists() and not force:
            continue

        path.parent.mkdir(parents=True, exist_ok=True)
        _write(kind, path)
        written.append(path)

    return written


def _write(kind: ObjectKind, path: Path) -> None:
    """Writes one format's document to ``path``."""
    if kind is ObjectKind.RECONSTRUCTION:
        corpus_reconstruction(corpus_instructions()).save(path)
        return

    if kind is ObjectKind.LIBRARY:
        corpus_library().save(path)
        return

    ProjectContainer.save(corpus_project(embedded_reconstruction()), path)
