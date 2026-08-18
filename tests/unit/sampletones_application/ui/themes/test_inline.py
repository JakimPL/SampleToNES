from typing import Dict, Generator, Set

import dearpygui.dearpygui as dpg
import pytest

from sampletones_application.ui.themes.inline import (
    create_header_selectable_theme,
    create_selectable_text_theme,
)
from sampletones_application.utils.palette.colors.written import LiteralColor
from sampletones_shared.types.application import ColorRGBA

TEXT_RGBA: ColorRGBA = (220, 220, 220, 255)
HOVERED_RGBA: ColorRGBA = (255, 255, 255, 64)
ACTIVE_RGBA: ColorRGBA = (255, 255, 255, 102)

TEXT_COLOR = LiteralColor(TEXT_RGBA)
HOVERED_COLOR = LiteralColor(HOVERED_RGBA)
ACTIVE_COLOR = LiteralColor(ACTIVE_RGBA)

ENABLED_STATES = (True, False)


def _components(theme: int) -> Dict[bool, int]:
    """The theme's components keyed by the enabled state each one answers for."""
    return {
        dpg.get_item_configuration(component)["enabled_state"]: component
        for component in dpg.get_item_children(theme, slot=1)
    }


def _item_types(theme: int) -> Set[int]:
    return {dpg.get_item_configuration(component)["item_type"] for component in dpg.get_item_children(theme, slot=1)}


def _colors(theme: int, *, enabled_state: bool) -> Dict[int, ColorRGBA]:
    """The colours one component carries, keyed by the DearPyGui colour they target."""
    component = _components(theme)[enabled_state]
    return {
        dpg.get_item_configuration(entry)["target"]: tuple(int(value) for value in dpg.get_value(entry))
        for entry in dpg.get_item_children(component, slot=1)
    }


@pytest.fixture
def context() -> Generator[None, None, None]:
    dpg.create_context()
    try:
        yield
    finally:
        dpg.destroy_context()


class TestSelectableTextTheme:
    def test_the_text_colour_is_the_theme_s_whole_claim(self, context: None) -> None:
        """A cell keeps the hover and selection shades of the table it sits in."""
        theme = create_selectable_text_theme(TEXT_COLOR)

        assert _colors(theme, enabled_state=True) == {dpg.mvThemeCol_Text: TEXT_RGBA}

    @pytest.mark.parametrize("enabled_state", ENABLED_STATES, ids=["enabled", "disabled"])
    def test_both_enabled_states_carry_the_colour(self, context: None, enabled_state: bool) -> None:
        theme = create_selectable_text_theme(TEXT_COLOR)

        assert _colors(theme, enabled_state=enabled_state)[dpg.mvThemeCol_Text] == TEXT_RGBA

    def test_the_theme_addresses_selectables(self, context: None) -> None:
        theme = create_selectable_text_theme(TEXT_COLOR)

        assert _item_types(theme) == {dpg.mvSelectable}


class TestHeaderSelectableTheme:
    @pytest.mark.parametrize("enabled_state", ENABLED_STATES, ids=["enabled", "disabled"])
    def test_the_label_carries_its_text_and_pointer_shades(self, context: None, enabled_state: bool) -> None:
        theme = create_header_selectable_theme(TEXT_COLOR, HOVERED_COLOR, ACTIVE_COLOR)

        assert _colors(theme, enabled_state=enabled_state) == {
            dpg.mvThemeCol_Text: TEXT_RGBA,
            dpg.mvThemeCol_HeaderHovered: HOVERED_RGBA,
            dpg.mvThemeCol_HeaderActive: ACTIVE_RGBA,
        }

    def test_the_resting_shade_stays_with_the_table(self, context: None) -> None:
        """The header row's own background is a table highlight, so the label leaves it alone."""
        theme = create_header_selectable_theme(TEXT_COLOR, HOVERED_COLOR, ACTIVE_COLOR)

        assert dpg.mvThemeCol_Header not in _colors(theme, enabled_state=True)

    def test_the_theme_addresses_selectables(self, context: None) -> None:
        theme = create_header_selectable_theme(TEXT_COLOR, HOVERED_COLOR, ACTIVE_COLOR)

        assert _item_types(theme) == {dpg.mvSelectable}

    def test_the_two_builders_produce_distinct_themes(self, context: None) -> None:
        text_theme = create_selectable_text_theme(TEXT_COLOR)
        header_theme = create_header_selectable_theme(TEXT_COLOR, HOVERED_COLOR, ACTIVE_COLOR)

        assert text_theme != header_theme
        assert len(_colors(header_theme, enabled_state=True)) > len(_colors(text_theme, enabled_state=True))
