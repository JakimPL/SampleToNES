from pathlib import Path
from typing import List

import pytest

from tests.unit.sampletones_tools.calibration.runs import write_run


@pytest.fixture(name="run")
def run_fixture(tmp_path: Path) -> Path:
    return write_run(tmp_path / "run-a", ["cqt-pe1", "fft-pe1"], 0.0)


@pytest.fixture(name="runs")
def runs_fixture(tmp_path: Path) -> List[Path]:
    return [
        write_run(tmp_path / "before", ["cqt-pe1", "fft-pe1"], 0.0),
        write_run(tmp_path / "after", ["cqt-pe1", "fft-pe1"], -1.0),
    ]
