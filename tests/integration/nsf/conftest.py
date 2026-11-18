from pathlib import Path
from typing import Dict

import pytest

from sampletones_core.project.voices.sample import Sample
from sampletones_shared.paths.extensions import EXT_FILE_NSF


@pytest.fixture
def nsf_paths(tmp_path: Path, instrument_catalog: Dict[str, Sample]) -> Dict[str, Path]:
    """Where each sample's produced ``.nsf`` is written."""
    return {name: tmp_path / f"{name}{EXT_FILE_NSF}" for name in instrument_catalog}
