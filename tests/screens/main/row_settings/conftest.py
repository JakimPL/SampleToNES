import pytest

from tests.screens.main.row_settings.steps import recordings
from tests.suite.screens.worlds.home import World
from tests.suite.screens.worlds.recordings import lived_in_world


@pytest.fixture
def world() -> World:
    """A lived-in home holding the kick and snare recordings and a folder of two takes."""
    return World(state=lived_in_world().state, application_config=None, config=None, files=recordings())
