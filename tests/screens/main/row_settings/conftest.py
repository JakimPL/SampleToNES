import pytest

from automation.worlds.home import World, lived_in_world
from tests.screens.main.row_settings.steps import recordings


@pytest.fixture
def world() -> World:
    """A lived-in home holding the kick and snare recordings and a folder of two takes."""
    return World(state=lived_in_world().state, application_config=None, config=None, files=recordings())
