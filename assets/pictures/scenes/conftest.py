import pytest

from assets.pictures.worlds import GUIDE_VIEWPORT, demo_world
from assets.pictures.writer import Pictures
from automation.plugin.fixtures import (
    output_device_fixture,
    screen_application_fixture,
    screen_boundaries_fixture,
    screen_bridge_fixture,
    screen_fixture,
    screen_render_thread_fixture,
    startup_fixture,
)
from automation.plugin.hold_fixtures import (
    conversion_hold_fixture,
    export_hold_fixture,
    regeneration_hold_fixture,
    scan_hold_fixture,
    screen_holds_fixture,
)
from automation.plugin.hooks import (
    pytest_collection_modifyitems,
    pytest_configure,
    pytest_pyfunc_call,
    pytest_runtest_protocol,
    pytest_unconfigure,
)
from automation.screen import Screen
from automation.worlds.home import World

__all__ = [
    "conversion_hold_fixture",
    "export_hold_fixture",
    "output_device_fixture",
    "pictures_fixture",
    "pytest_collection_modifyitems",
    "pytest_configure",
    "pytest_pyfunc_call",
    "pytest_runtest_protocol",
    "pytest_unconfigure",
    "regeneration_hold_fixture",
    "scan_hold_fixture",
    "screen_application_fixture",
    "screen_boundaries_fixture",
    "screen_bridge_fixture",
    "screen_fixture",
    "screen_holds_fixture",
    "screen_render_thread_fixture",
    "startup_fixture",
    "world_fixture",
]


@pytest.fixture(name="world")
def world_fixture() -> World:
    """A home holding the demo tree, at the window size the guide's pictures are drawn at."""
    return demo_world(GUIDE_VIEWPORT)


@pytest.fixture(name="pictures")
def pictures_fixture(screen: Screen) -> Pictures:
    """What a scene writes its pictures with."""
    return Pictures(screen)
