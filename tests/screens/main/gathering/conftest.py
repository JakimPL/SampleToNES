from pathlib import Path
from typing import Final, List

import pytest

from automation.steps.main import home_path
from automation.worlds.home import HomeFile, World, lived_in_world
from tests.screens.main.gathering.constants import (
    COLLIDING,
    INNER,
    LOOPS,
    LOOPS_HELD,
    NOTES,
    TAKES,
    TAKES_AT_THE_TOP,
    TAKES_INSIDE,
)
from tests.suite.screens.seeds.archives import WrittenBytes
from tests.suite.screens.seeds.constants import KICK, SNARE
from tests.suite.screens.seeds.recordings import Recording

PLAYED_SECONDS: Final[float] = 2.0
SHORT_SECONDS: Final[float] = 0.2
TONE_FREQUENCY: Final[float] = 220.0
NOTE_TEXT: Final[bytes] = b"A folder holding words, not sounds.\n"


def recording(path: Path, seconds: float) -> HomeFile:
    """Returns a seeded tone recording of ``seconds`` to be written at ``path``."""
    return Recording(destination=path, seconds=seconds, frequency=TONE_FREQUENCY)


def gathering_world() -> World:
    """Returns the lived-in world plus two long recordings, the Takes folder with a subfolder, the Loops
    folder, three recordings with colliding names and a Notes folder holding only a text file.
    """
    files: List[HomeFile] = [
        recording(home_path(KICK), PLAYED_SECONDS),
        recording(home_path(SNARE), PLAYED_SECONDS),
        *(recording(home_path(TAKES) / name, SHORT_SECONDS) for name in TAKES_AT_THE_TOP),
        *(recording(home_path(TAKES) / INNER / name, SHORT_SECONDS) for name in TAKES_INSIDE),
        *(recording(home_path(LOOPS) / name, SHORT_SECONDS) for name in LOOPS_HELD),
        *(recording(home_path(name), SHORT_SECONDS) for name in COLLIDING),
        WrittenBytes(home_path(NOTES) / INNER / "readme.txt", NOTE_TEXT),
    ]
    world = lived_in_world()
    return World(
        state=world.state,
        application_config=world.application_config,
        config=world.config,
        files=tuple(files),
    )


@pytest.fixture
def world() -> World:
    """The home holds the recordings and folders the gathering scenarios pick from."""
    return gathering_world()
