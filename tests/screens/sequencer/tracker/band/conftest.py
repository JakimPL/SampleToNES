import pytest

from tests.suite.screens.application.startup import Startup
from tests.suite.screens.worlds.home import World
from tests.suite.screens.worlds.songs import (
    LOOPING_ORDER_FRAMES,
    LOOPING_PROJECT,
    arranged_project,
    sequencer_world,
)


@pytest.fixture
def world() -> World:
    """The Sequencer's home, holding besides the arranged project with its pattern played twice in the order."""
    sequencer = sequencer_world()
    return World(
        state=sequencer.state,
        application_config=None,
        config=None,
        files=(
            *sequencer.files,
            arranged_project(LOOPING_PROJECT, LOOPING_ORDER_FRAMES),
        ),
    )


@pytest.fixture
def startup() -> Startup:
    """The application opens on the two-frame song with no reconstruction loaded."""
    return Startup(reconstruction=None, project=LOOPING_PROJECT)
