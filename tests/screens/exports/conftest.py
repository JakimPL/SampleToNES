import pytest

from tests.suite.screens.worlds.home import World
from tests.suite.screens.worlds.songs import exporting_world


@pytest.fixture
def world() -> World:
    """The home every export scenario starts in: the arranged project, and projects meeting an export's limits."""
    return exporting_world()
