import pytest

from tests.suite.screens.worlds.home import World
from tests.suite.screens.worlds.recordings import documents_world


@pytest.fixture
def world() -> World:
    """The home every prompt scenario starts in: documents to put away and replace, and recordings to convert."""
    return documents_world()
