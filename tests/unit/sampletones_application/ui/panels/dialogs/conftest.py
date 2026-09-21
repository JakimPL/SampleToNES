from typing import Iterator
from unittest.mock import patch

import dearpygui.dearpygui as dpg
import pytest

from sampletones_application.layout.config import LayoutConfig
from sampletones_application.layout.loader import load_layout_config
from sampletones_application.paths import (
    BEHAVIOR_DIRECTORY,
    LAYOUT_DIRECTORY,
    PALETTES_DIRECTORY,
    THEME_DIRECTORY,
)
from sampletones_application.ui.elements.fonts.registry import FontRegistry
from sampletones_application.ui.themes.registry import ThemeRegistry
from sampletones_application.ui.themes.setup import setup_themes
from sampletones_application.utils.palette.catalog import PaletteCatalog
from sampletones_application.utils.palette.source import PaletteSource


@pytest.fixture
def layout_config() -> LayoutConfig:
    source = PaletteSource(PaletteCatalog.load(PALETTES_DIRECTORY).default)
    return load_layout_config(LAYOUT_DIRECTORY, BEHAVIOR_DIRECTORY, source)


@pytest.fixture
def dpg_context(layout_config: LayoutConfig) -> Iterator[None]:
    """Stands up the context, fonts and themes a dialog resolves on construction, as startup does."""
    dpg.create_context()
    FontRegistry.setup(layout_config.fonts)
    FontRegistry.register_fonts(layout_config.fonts.scale)
    setup_themes(THEME_DIRECTORY, PaletteSource(PaletteCatalog.load(PALETTES_DIRECTORY).default))
    try:
        yield
    finally:
        ThemeRegistry.clear()
        dpg.destroy_context()


@pytest.fixture(autouse=True)
def viewport(layout_config: LayoutConfig) -> Iterator[None]:
    """Stands in for the viewport a dialog is centered against, which a suite draws none of."""
    window = layout_config.general.window
    with (
        patch.object(dpg, "get_viewport_client_width", return_value=window.width),
        patch.object(dpg, "get_viewport_client_height", return_value=window.height),
    ):
        yield
