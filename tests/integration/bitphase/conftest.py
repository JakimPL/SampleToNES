from pathlib import Path
from typing import Optional

import pytest

from tests.integration.output import resolve_output_directory, resolve_output_path
from tests.integration.paths import (
    BTP_OUTPUT_ENV,
    DOCUMENT_FILENAME,
    GROOVE_DOCUMENT_FILENAME,
)


@pytest.fixture(scope="session")
def btp_output_dir() -> Optional[Path]:
    """The persistent output directory ``SAMPLETONES_BTP_OUTPUT_DIR`` names."""
    return resolve_output_directory(BTP_OUTPUT_ENV)


@pytest.fixture
def document_path(btp_output_dir: Optional[Path], tmp_path: Path) -> Path:
    """Where a produced ``.btp`` is written."""
    return resolve_output_path(btp_output_dir, tmp_path, DOCUMENT_FILENAME)


@pytest.fixture
def groove_document_path(btp_output_dir: Optional[Path], tmp_path: Path) -> Path:
    """Where the document carrying a groove is written, beside the one at the song's own tempo."""
    return resolve_output_path(btp_output_dir, tmp_path, GROOVE_DOCUMENT_FILENAME)
