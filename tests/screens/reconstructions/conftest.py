import pytest

from tests.suite.screens.world import World, playing_world


@pytest.fixture
def world() -> World:
    """The home every Reconstructions scenario starts in: reconstructions that play, and a project."""
    return playing_world()
