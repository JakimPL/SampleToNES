from pathlib import Path
from typing import Final

import pytest

from tests.screens.main.run.constants import ALBUM, ALBUM_TAKES, BASS, DISC, DISC_TAKES, DRUMS, LEAD
from tests.suite.screens.seeds.recordings import Recording
from tests.suite.screens.steps.main import home_path
from tests.suite.screens.worlds.home import HomeFile, World
from tests.suite.screens.worlds.recordings import converting_world

SECONDS: Final[float] = 0.3
FREQUENCY: Final[float] = 220.0


def recording(path: Path) -> HomeFile:
    """A short recording to be written at ``path``."""
    return Recording(destination=path, seconds=SECONDS, frequency=FREQUENCY)


def run_world() -> World:
    """A home holding three recordings and an Album folder with a nested Disc2 folder, set up to convert."""
    paths = [
        home_path(BASS),
        home_path(LEAD),
        home_path(DRUMS),
        *(home_path(ALBUM) / name for name in ALBUM_TAKES),
        *(home_path(ALBUM) / DISC / name for name in DISC_TAKES),
    ]
    return converting_world(tuple(recording(path) for path in paths))


@pytest.fixture
def world() -> World:
    """The world of ``run_world``."""
    return run_world()
