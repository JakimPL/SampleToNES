import pytest

from automation.application.startup import Startup
from automation.worlds.home import World
from tests.suite.screens.worlds.history import HISTORY_PROJECT, history_world


@pytest.fixture
def world() -> World:
    """The home every history scenario starts in: the project with something in every part a gesture reaches."""
    return history_world()


@pytest.fixture
def startup() -> Startup:
    """The application opens on that project with no reconstruction loaded."""
    return Startup(reconstruction=None, project=HISTORY_PROJECT)
