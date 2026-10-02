import pytest

from tests.suite.screens.world import World, exporting_world


@pytest.fixture
def world() -> World:
    """The home every export scenario starts in: the arranged project, and projects meeting an export's limits."""
    return exporting_world()
