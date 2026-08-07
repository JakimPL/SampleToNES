from pathlib import Path
from typing import Dict, Generator, NamedTuple

import dearpygui.dearpygui as dpg
import pytest

from sampletones_application.ui.themes.loader import ThemeLoader
from sampletones_application.ui.themes.theme import Theme
from sampletones_application.utils.gui.palette.palette import PaletteBindings
from sampletones_application.utils.palette.palette import Palette
from sampletones_application.utils.palette.source import PaletteSource
from sampletones_shared.types.application import ColorRGBA

_THEME = """
name: default
tag: synthetic.default
components:
  - item_type: All
    entries:
      - type: color
        key: Text
        value: .text
      - type: color
        key: WindowBg
        value: "#242424ff"
"""

_STUDIO = """
name: studio

colors:
    text: "#dcdcdc"
"""

_LIGHT = """
name: light

colors:
    text: "#1e1e24"
"""

STUDIO_TEXT: ColorRGBA = (220, 220, 220, 255)
LIGHT_TEXT: ColorRGBA = (30, 30, 36, 255)
LITERAL_BACKGROUND: ColorRGBA = (36, 36, 36, 255)


class _Styled(NamedTuple):
    """A created theme and the source whose palette its colours read."""

    theme: Theme
    source: PaletteSource


def _live_colors(theme: Theme) -> Dict[int, ColorRGBA]:
    """The colours DearPyGui holds for the theme's enabled ``All`` component, keyed by target."""
    component = dpg.get_item_children(theme.tag, slot=1)[0]
    return {
        dpg.get_item_configuration(entry)["target"]: tuple(int(channel) for channel in dpg.get_value(entry))
        for entry in dpg.get_item_children(component, slot=1)
    }


@pytest.fixture
def styled(tmp_path: Path) -> Generator[_Styled, None, None]:
    themes_path = tmp_path / "themes"
    themes_path.mkdir(parents=True, exist_ok=True)
    (themes_path / "default.yaml").write_text(_THEME)
    (tmp_path / "studio.yaml").write_text(_STUDIO)
    (tmp_path / "light.yaml").write_text(_LIGHT)

    source = PaletteSource(Palette.load(tmp_path / "studio.yaml"))
    dpg.create_context()
    try:
        theme = ThemeLoader(themes_path, source).load_all()[0]
        theme.create()
        yield _Styled(theme=theme, source=source)
    finally:
        dpg.destroy_context()


@pytest.fixture
def light(tmp_path: Path) -> Palette:
    return Palette.load(tmp_path / "light.yaml")


class TestCreate:
    def test_the_theme_is_built_once_for_its_tag(self, styled: _Styled) -> None:
        components = dpg.get_item_children(styled.theme.tag, slot=1)

        styled.theme.create()

        assert dpg.get_item_children(styled.theme.tag, slot=1) == components

    def test_a_referenced_colour_reaches_dearpygui_resolved(self, styled: _Styled) -> None:
        assert _live_colors(styled.theme)[dpg.mvThemeCol_Text] == STUDIO_TEXT


class TestRestyle:
    """A palette swap reaches themed widgets by rewriting the colour items already created."""

    def test_a_referenced_colour_takes_the_newly_activated_palette(
        self,
        styled: _Styled,
        light: Palette,
    ) -> None:
        styled.source.activate(light)
        PaletteBindings.apply()

        assert _live_colors(styled.theme)[dpg.mvThemeCol_Text] == LIGHT_TEXT

    def test_a_literal_colour_stays_as_written(self, styled: _Styled, light: Palette) -> None:
        styled.source.activate(light)
        PaletteBindings.apply()

        assert _live_colors(styled.theme)[dpg.mvThemeCol_WindowBg] == LITERAL_BACKGROUND

    def test_the_reported_colour_follows_the_palette_before_any_restyle(
        self,
        styled: _Styled,
        light: Palette,
    ) -> None:
        styled.source.activate(light)

        assert styled.theme.get_color(dpg.mvAll, dpg.mvThemeCol_Text) == LIGHT_TEXT
