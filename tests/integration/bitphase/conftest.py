from pathlib import Path

import pytest

from sampletones_tools.samples.bitphase import DOCUMENT_FILENAME, GROOVE_DOCUMENT_FILENAME


@pytest.fixture
def document_path(tmp_path: Path) -> Path:
    """Where a produced ``.btp`` is written."""
    return tmp_path / DOCUMENT_FILENAME


@pytest.fixture
def groove_document_path(tmp_path: Path) -> Path:
    """Where the document carrying a groove is written, beside the one at the song's own tempo."""
    return tmp_path / GROOVE_DOCUMENT_FILENAME
