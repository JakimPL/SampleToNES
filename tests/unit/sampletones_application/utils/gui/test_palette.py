from typing import Dict, Generator

import dearpygui.dearpygui as dpg
import pytest

from sampletones_application.utils.gui.palette.dpg import (
    dpg_add_palette_theme_color,
    dpg_set_palette_color,
)
from sampletones_application.utils.gui.palette.palette import PaletteBindings
from sampletones_application.utils.palette.colors.base import BaseColor
from sampletones_application.utils.palette.colors.faded import FadedColor
from sampletones_application.utils.palette.colors.literal import LiteralColor
from sampletones_application.utils.palette.colors.named import NamedColor
from sampletones_application.utils.palette.palette import Palette
from sampletones_application.utils.palette.reference import PaletteReference
from sampletones_application.utils.palette.source import PaletteSource
from sampletones_shared.types.application import ColorRGBA, Sender
from sampletones_shared.utils.color import MAX_CHANNEL_VALUE

STUDIO_ACCENT: ColorRGBA = (169, 127, 227, 255)
LIGHT_ACCENT: ColorRGBA = (107, 63, 176, 255)
LITERAL: ColorRGBA = (240, 146, 86, 255)


@pytest.fixture
def source() -> PaletteSource:
    return PaletteSource(Palette.model_validate({"name": "studio", "colors": {"accent": "#a97fe3"}}))


@pytest.fixture
def light() -> Palette:
    return Palette.model_validate({"name": "light", "colors": {"accent": "#6b3fb0"}})


@pytest.fixture
def accent(source: PaletteSource) -> BaseColor:
    return NamedColor(reference=PaletteReference(token="accent"), source=source)


@pytest.fixture
def context() -> Generator[None, None, None]:
    dpg.create_context()
    try:
        yield
    finally:
        dpg.destroy_context()


def _text_color(item: Sender) -> ColorRGBA:
    """The item's colour as eight-bit channels, which DearPyGui reports as fractions."""
    configuration: Dict[str, object] = dpg.get_item_configuration(item)
    color = configuration["color"]
    assert isinstance(color, (list, tuple))
    red, green, blue, alpha = (round(channel * MAX_CHANNEL_VALUE) for channel in color)
    return red, green, blue, alpha


def _add_text() -> Sender:
    with dpg.window():
        return dpg.add_text("value")


class TestArgumentBinding:
    def test_the_colour_reaches_the_item_as_it_is_bound(
        self,
        context: None,
        accent: BaseColor,
    ) -> None:
        item = _add_text()

        dpg_set_palette_color(item, accent)

        assert _text_color(item) == STUDIO_ACCENT

    def test_the_item_takes_the_newly_activated_palette(
        self,
        context: None,
        source: PaletteSource,
        accent: BaseColor,
        light: Palette,
    ) -> None:
        item = _add_text()
        dpg_set_palette_color(item, accent)

        source.activate(light)
        PaletteBindings.apply()

        assert _text_color(item) == LIGHT_ACCENT

    def test_a_literal_colour_stays_as_written(
        self,
        context: None,
        source: PaletteSource,
        light: Palette,
    ) -> None:
        item = _add_text()
        dpg_set_palette_color(item, LiteralColor(LITERAL))

        source.activate(light)
        PaletteBindings.apply()

        assert _text_color(item) == LITERAL

    def test_recolouring_one_argument_leaves_one_entry(
        self,
        context: None,
        accent: BaseColor,
    ) -> None:
        """A hovered item is recoloured on every frame it is under the pointer."""
        item = _add_text()

        for _ in range(5):
            dpg_set_palette_color(item, accent)

        assert len(list(PaletteBindings.bindings())) == 1

    def test_a_deleted_item_is_dropped(
        self,
        context: None,
        accent: BaseColor,
    ) -> None:
        item = _add_text()
        dpg_set_palette_color(item, accent)
        dpg.delete_item(item)

        PaletteBindings.apply()

        assert not list(PaletteBindings.bindings())


class TestThemeColorBinding:
    def test_the_theme_colour_takes_the_newly_activated_palette(
        self,
        context: None,
        source: PaletteSource,
        accent: BaseColor,
        light: Palette,
    ) -> None:
        with dpg.theme():
            with dpg.theme_component(dpg.mvAll):
                item = dpg_add_palette_theme_color(dpg.mvThemeCol_Text, accent)

        source.activate(light)
        PaletteBindings.apply()

        assert tuple(int(channel) for channel in dpg.get_value(item)) == LIGHT_ACCENT

    def test_a_derived_colour_follows_the_colour_it_came_from(
        self,
        context: None,
        source: PaletteSource,
        accent: BaseColor,
        light: Palette,
    ) -> None:
        with dpg.theme():
            with dpg.theme_component(dpg.mvAll):
                item = dpg_add_palette_theme_color(
                    dpg.mvThemeCol_Text,
                    FadedColor(color=accent, fraction=0.5),
                )

        source.activate(light)
        PaletteBindings.apply()

        red, green, blue, _ = LIGHT_ACCENT
        assert tuple(int(channel) for channel in dpg.get_value(item)) == (
            red,
            green,
            blue,
            128,
        )
