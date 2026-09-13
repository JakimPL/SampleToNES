from pathlib import Path

import pytest

from sampletones_tools.samples.famitracker import MODULE_FILENAME


@pytest.fixture
def module_path(tmp_path: Path) -> Path:
    """Where a produced ``.ftm`` is written."""
    return tmp_path / MODULE_FILENAME
