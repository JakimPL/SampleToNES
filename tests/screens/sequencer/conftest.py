import pytest

from automation.application.startup import Startup
from automation.worlds.home import World
from tests.suite.screens.worlds.songs import ARRANGED_PROJECT, sequencer_world


@pytest.fixture
def world() -> World:
    """The home every Sequencer scenario starts in: an arranged project, and reconstructions to add to it."""
    return sequencer_world()


@pytest.fixture
def startup() -> Startup:
    """The application opens on the arranged project with no reconstruction loaded."""
    return Startup(reconstruction=None, project=ARRANGED_PROJECT)
