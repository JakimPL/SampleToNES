import pytest

from sampletones_application.layout.graphs import GraphsLayout
from sampletones_application.layout.loader import load_layout_config
from sampletones_application.paths import (
    BEHAVIOR_DIRECTORY,
    LAYOUT_DIRECTORY,
    PALETTES_DIRECTORY,
)
from sampletones_application.utils.palette.catalog import PaletteCatalog
from sampletones_application.utils.palette.source import PaletteSource


@pytest.fixture
def graphs_layout() -> GraphsLayout:
    """The graph settings the build ships, read where they are configured."""
    source = PaletteSource(PaletteCatalog.load(PALETTES_DIRECTORY).default)
    return load_layout_config(LAYOUT_DIRECTORY, BEHAVIOR_DIRECTORY, source).graphs
