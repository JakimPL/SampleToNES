import pytest

from tests.suite.screens.application.startup import Startup
from tests.suite.screens.worlds.songs import ARRANGED_PROJECT


@pytest.fixture
def startup() -> Startup:
    """The home opens with the arranged project and no reconstruction."""
    return Startup(reconstruction=None, project=ARRANGED_PROJECT)
