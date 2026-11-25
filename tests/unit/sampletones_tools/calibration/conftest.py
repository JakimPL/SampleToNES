from pathlib import Path
from typing import Tuple

import pytest

from tests.unit.sampletones_tools.calibration.source_tree import write_source


@pytest.fixture(name="packages")
def packages_fixture(tmp_path: Path) -> Tuple[Path, ...]:
    return write_source(tmp_path / "source")
