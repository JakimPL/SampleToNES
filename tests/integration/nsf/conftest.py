from pathlib import Path
from typing import Dict, Final

import pytest

from sampletones_core.project.voices.sample import Sample
from sampletones_player.builder import song_from_reconstruction
from sampletones_player.compression.scheme import CompressionScheme
from sampletones_player.driver.image import DriverImage
from sampletones_player.song import Song
from sampletones_shared.paths.extensions import EXT_FILE_NSF

EXPORTED_SAMPLE: Final[str] = "lead"


@pytest.fixture
def nsf_paths(tmp_path: Path, instrument_catalog: Dict[str, Sample]) -> Dict[str, Path]:
    """Where each sample's produced ``.nsf`` is written."""
    return {name: tmp_path / f"{name}{EXT_FILE_NSF}" for name in instrument_catalog}


@pytest.fixture(scope="session")
def driver_image() -> DriverImage:
    """The assembled driver every exported file carries."""
    return DriverImage.load()


@pytest.fixture
def sample(instrument_catalog: Dict[str, Sample]) -> Sample:
    """The sample the structural cases read, covering both pulse channels."""
    return instrument_catalog[EXPORTED_SAMPLE]


@pytest.fixture
def song(sample: Sample) -> Song:
    """The song the console plays that sample as."""
    return song_from_reconstruction(sample.reconstruction, loop_tick=None, scheme=CompressionScheme.SEARCH)
