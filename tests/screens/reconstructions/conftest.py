import pytest

from automation.worlds.home import World
from tests.suite.screens.worlds.recordings import playing_world


@pytest.fixture
def world() -> World:
    """The home every Reconstructions scenario starts in: reconstructions that play, and a project."""
    return playing_world()
