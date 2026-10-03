import pytest

from tests.suite.screens.worlds.home import World
from tests.suite.screens.worlds.recordings import converting_world


@pytest.fixture
def world() -> World:
    """The home every Instructions scenario starts in: a small library built for one-worker settings."""
    return converting_world(())
