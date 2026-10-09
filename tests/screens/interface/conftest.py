import pytest

from automation.worlds.home import World
from tests.suite.screens.worlds.songs import sequencer_world


@pytest.fixture
def world() -> World:
    """The home every interface scenario starts in: an arranged project and reconstructions that play."""
    return sequencer_world()
