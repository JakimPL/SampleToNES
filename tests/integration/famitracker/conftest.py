import os
import shutil
from pathlib import Path
from typing import Optional

import pytest

from tests.integration.paths import FTM_OUTPUT_ENV, MODULE_FILENAME, REPO_ROOT


@pytest.fixture(scope="session")
def ftm_output_dir() -> Optional[Path]:
    """The persistent output directory, or None when emission is not requested.

    Emission is opt-in via the ``SAMPLETONES_FTM_OUTPUT_DIR`` environment variable so
    ordinary (and parallel) runs write only to ``tmp_path``. When set, the directory
    is cleaned once per session so each run leaves a fresh set of files.
    """
    configured = os.environ.get(FTM_OUTPUT_ENV)
    if not configured:
        return None

    directory = Path(configured)
    if not directory.is_absolute():
        directory = REPO_ROOT / directory

    if directory.exists():
        shutil.rmtree(directory)

    directory.mkdir(parents=True, exist_ok=True)
    return directory


@pytest.fixture
def module_path(ftm_output_dir: Optional[Path], tmp_path: Path) -> Path:
    """Where a produced ``.ftm`` is written: the persistent dir if opted in, else tmp."""
    base = ftm_output_dir if ftm_output_dir is not None else tmp_path
    return base / MODULE_FILENAME
