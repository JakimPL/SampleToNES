import pytest

from tests.suite.screens.world import World, converting_world


@pytest.fixture
def world() -> World:
    """The home every Instructions scenario starts in: a small library built for one-worker settings."""
    return converting_world(())
