from typing import Final, List

import pytest

from tests.screens.main.list.constants import FORTY, FORTY_COUNT
from tests.screens.main.list.steps import recording, take
from tests.suite.screens.steps.main import home_path
from tests.suite.screens.vocabulary.recordings import KICK, SNARE
from tests.suite.screens.worlds.home import HomeFile, World
from tests.suite.screens.worlds.recordings import lived_in_world

PLAYED_SECONDS: Final[float] = 2.0
SHORT_SECONDS: Final[float] = 0.02


@pytest.fixture
def world() -> World:
    """The home holds the Kick and Snare recordings and a Forty folder of short takes."""
    files: List[HomeFile] = [
        recording(home_path(KICK), PLAYED_SECONDS),
        recording(home_path(SNARE), PLAYED_SECONDS),
        *(recording(home_path(FORTY) / take(index), SHORT_SECONDS) for index in range(FORTY_COUNT)),
    ]
    return World(state=lived_in_world().state, application_config=None, config=None, files=tuple(files))
