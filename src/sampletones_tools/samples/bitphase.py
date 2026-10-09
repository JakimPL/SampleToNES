from pathlib import Path
from typing import Final, List

from sampletones_core.formats.bitphase.btp import write_btp
from sampletones_core.formats.bitphase.builder import project_to_bitphase
from sampletones_core.project.project import Project
from sampletones_tools.corpus.build import Corpus

DOCUMENT_FILENAME: Final[str] = "drums.btp"
GROOVE_DOCUMENT_FILENAME: Final[str] = "drums-groove.btp"
GROOVE_TEMPO: Final[int] = 210


def at_tempo(project: Project, tempo: int) -> Project:
    """The same project played at another tempo, leaving the given project as it is."""
    return Project(
        metadata=project.metadata,
        info=project.info,
        settings=project.settings.model_copy(update={"tempo": tempo}),
        voices=project.voices,
        song=project.song,
    )


def write_samples(corpus: Corpus, output: Path) -> List[Path]:
    """Writes the corpus arrangement as two Bitphase documents: at its own tempo and as a groove.

    Args:
        corpus: The samples and the arrangement.
        output: The directory the documents are written into.

    Returns:
        List[Path]: The document at the song's tempo, then the one carrying a groove.
    """
    document = output / DOCUMENT_FILENAME
    write_btp(document, project_to_bitphase(corpus.project))
    groove_document = output / GROOVE_DOCUMENT_FILENAME
    write_btp(groove_document, project_to_bitphase(at_tempo(corpus.project, GROOVE_TEMPO)))
    return [document, groove_document]
