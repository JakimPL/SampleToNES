import pytest

from assets.pictures.worlds import GUIDE_VIEWPORT, demo_world
from assets.pictures.writer import Pictures
from automation.screen import Screen
from automation.worlds.home import World


@pytest.fixture(name="world")
def world_fixture() -> World:
    """A home holding the demo tree, at the window size the guide's pictures are drawn at."""
    return demo_world(GUIDE_VIEWPORT)


@pytest.fixture(name="pictures")
def pictures_fixture(screen: Screen) -> Pictures:
    """What a scene writes its pictures with."""
    return Pictures(screen)
