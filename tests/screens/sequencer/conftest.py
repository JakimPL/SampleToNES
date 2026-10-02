import pytest

from tests.suite.screens.world import World, sequencer_world


@pytest.fixture
def world() -> World:
    """The home every Sequencer scenario starts in: an arranged project, and reconstructions to add to it."""
    return sequencer_world()
