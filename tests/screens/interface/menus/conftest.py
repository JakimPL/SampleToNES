import pytest

from tests.suite.screens.application.startup import Startup
from tests.suite.screens.worlds.recordings import PLAYABLE_RECONSTRUCTION
from tests.suite.screens.worlds.songs import ARRANGED_PROJECT


@pytest.fixture
def startup() -> Startup:
    """Opens the application with a playable reconstruction and the arranged project."""
    return Startup(reconstruction=PLAYABLE_RECONSTRUCTION, project=ARRANGED_PROJECT)
