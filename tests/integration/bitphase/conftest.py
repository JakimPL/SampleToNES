from pathlib import Path

import pytest

from sampletones_core.formats.bitphase.btp import write_btp
from sampletones_core.formats.bitphase.builder import project_to_bitphase
from sampletones_core.formats.bitphase.specification.channels import CHANNEL_LABELS
from sampletones_core.project.project import Project
from sampletones_tools.samples.bitphase import DOCUMENT_FILENAME, GROOVE_DOCUMENT_FILENAME
from tests.suite.bitphase import LoadedProject, parse_btp


@pytest.fixture
def document_path(tmp_path: Path) -> Path:
    """Where a produced ``.btp`` is written."""
    return tmp_path / DOCUMENT_FILENAME


@pytest.fixture
def groove_document_path(tmp_path: Path) -> Path:
    """Where the document carrying a groove is written, beside the one at the song's own tempo."""
    return tmp_path / GROOVE_DOCUMENT_FILENAME


@pytest.fixture
def document(integration_project: Project, document_path: Path) -> LoadedProject:
    """The synthetic project written as a document and read back the way Bitphase loads it."""
    write_btp(document_path, project_to_bitphase(integration_project))
    return parse_btp(document_path.read_bytes(), list(CHANNEL_LABELS))
