from pathlib import Path
from typing import Optional

import pytest

from tests.integration.output import resolve_output_directory, resolve_output_path
from tests.integration.paths import FTM_OUTPUT_ENV, MODULE_FILENAME


@pytest.fixture(scope="session")
def ftm_output_dir() -> Optional[Path]:
    """The persistent output directory ``SAMPLETONES_FTM_OUTPUT_DIR`` names."""
    return resolve_output_directory(FTM_OUTPUT_ENV)


@pytest.fixture
def module_path(ftm_output_dir: Optional[Path], tmp_path: Path) -> Path:
    """Where a produced ``.ftm`` is written."""
    return resolve_output_path(ftm_output_dir, tmp_path, MODULE_FILENAME)
