import pytest

from tests.suite.screens.world import World, sequencer_world


@pytest.fixture
def world() -> World:
    """The home every interface scenario starts in: an arranged project and reconstructions that play."""
    return sequencer_world()
