from dataclasses import dataclass
from typing import Iterator

import dearpygui.dearpygui as dpg
import pytest

from sampletones_application.constants.general import TAG_GLOBAL_THEME_PANEL_SURFACE
from sampletones_application.ui.elements.layout.card import card
from sampletones_application.ui.themes.items import ThemeItems
from sampletones_application.ui.themes.registry import ThemeRegistry
from sampletones_application.ui.themes.theme import Theme

_CARD_TAG = "test_card"
_BODY_TAG = "test_card_body"


@pytest.fixture
def dpg_context() -> Iterator[None]:
    dpg.create_context()
    try:
        yield
    finally:
        dpg.destroy_context()


@pytest.fixture
def surface_theme(dpg_context: None) -> Iterator[Theme]:
    theme = Theme(tag=TAG_GLOBAL_THEME_PANEL_SURFACE, items=ThemeItems())
    ThemeRegistry.register(theme)
    try:
        yield theme
    finally:
        ThemeRegistry._registry.pop(TAG_GLOBAL_THEME_PANEL_SURFACE, None)


@dataclass(frozen=True)
class CardGeometry:
    label: str
    width: int = -1
    height: int = 0
    auto_resize_y: bool = True
    no_scrollbar: bool = False
    show: bool = True


_GEOMETRIES = [
    CardGeometry("auto_resize"),
    CardGeometry("fixed_size", width=200, height=120, auto_resize_y=False),
    CardGeometry("fill_height", width=0, height=-1, auto_resize_y=False),
    CardGeometry("hidden", show=False),
    CardGeometry("no_scrollbar", width=0, no_scrollbar=True),
]


class TestCard:
    """``card`` is the single primitive every panel roots its subtree on: it opens a
    container at the requested tag inside the coordinator-injected parent and hands that
    tag back, so a panel builds all its content there whatever the card's geometry."""

    @pytest.mark.parametrize("geometry", _GEOMETRIES, ids=lambda geometry: geometry.label)
    def test_roots_the_subtree_at_the_requested_tag(self, surface_theme: Theme, geometry: CardGeometry) -> None:
        with dpg.window() as parent:
            with card(
                parent,
                _CARD_TAG,
                width=geometry.width,
                height=geometry.height,
                auto_resize_y=geometry.auto_resize_y,
                no_scrollbar=geometry.no_scrollbar,
                show=geometry.show,
            ) as body_tag:
                dpg.add_text("content", tag=_BODY_TAG)

        assert body_tag == _CARD_TAG
        assert dpg.does_item_exist(_CARD_TAG)
        assert dpg.get_item_parent(_CARD_TAG) == parent
        assert dpg.get_item_parent(_BODY_TAG) == _CARD_TAG

    def test_binds_the_depth_theme_passed_to_it(self, dpg_context: None) -> None:
        toolbar_tag = "test_card_toolbar_theme"
        ThemeRegistry.register(Theme(tag=toolbar_tag, items=ThemeItems()))
        try:
            with dpg.window() as parent:
                with card(parent, _CARD_TAG, theme=toolbar_tag):
                    dpg.add_text("content")

            assert dpg.does_item_exist(_CARD_TAG)
            assert dpg.does_item_exist(toolbar_tag)
        finally:
            ThemeRegistry._registry.pop(toolbar_tag, None)
