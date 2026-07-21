import pytest

from sampletones_application.layout.config import LayoutConfig
from sampletones_application.layout.loader import load_layout_config
from sampletones_application.paths import BEHAVIOR_DIRECTORY, LAYOUT_DIRECTORY, PALETTE_PATH
from sampletones_application.utils.palette import Palette


@pytest.fixture
def layout_config() -> LayoutConfig:
    return load_layout_config(LAYOUT_DIRECTORY, BEHAVIOR_DIRECTORY, Palette.load(PALETTE_PATH))
