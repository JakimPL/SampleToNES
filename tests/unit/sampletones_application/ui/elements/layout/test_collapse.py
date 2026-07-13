from typing import Iterator, List, Tuple

import dearpygui.dearpygui as dpg
import pytest

from sampletones_application.layout.general import CollapseLayout, SectionHeaderLayout
from sampletones_application.layout.glyphs import CommonGlyphs, GlyphLayout, Glyphs
from sampletones_application.tags.general import (
    TAG_GLOBAL_THEME_COLLAPSE_HEADER,
    TAG_GLOBAL_THEME_COLLAPSE_HEADER_HOVERED,
    TAG_GLOBAL_THEME_SECTION_HEADER,
)
from sampletones_application.ui.elements.fonts.registry import FontRegistry
from sampletones_application.ui.elements.layout.collapse import (
    CollapseAxis,
    CollapseController,
)
from sampletones_application.ui.elements.panel import GUIPanel
from sampletones_application.ui.themes.items import ThemeItems
from sampletones_application.ui.themes.registry import ThemeRegistry
from sampletones_application.ui.themes.theme import Theme

_EXPANDED_GLYPH = "v"
_COLLAPSED_GLYPH = ">"
_CHEVRON_LEFT_GLYPH = "L"
_CHEVRON_RIGHT_GLYPH = "R"
_CARD_TAG = "test.card"
_EXPANDED_HEIGHT = 200
_HEADER_BAR_HEIGHT = 32
_RAIL_WIDTH = 28


_STRIP_PADDING = 8


@pytest.fixture
def dpg_context() -> Iterator[None]:
    dpg.create_context()
    ThemeRegistry.register(Theme(tag=TAG_GLOBAL_THEME_COLLAPSE_HEADER, items=ThemeItems()))
    ThemeRegistry.register(Theme(tag=TAG_GLOBAL_THEME_COLLAPSE_HEADER_HOVERED, items=ThemeItems()))
    ThemeRegistry.register(Theme(tag=TAG_GLOBAL_THEME_SECTION_HEADER, items=ThemeItems()))
    try:
        yield
    finally:
        ThemeRegistry._registry.pop(TAG_GLOBAL_THEME_COLLAPSE_HEADER, None)
        ThemeRegistry._registry.pop(TAG_GLOBAL_THEME_COLLAPSE_HEADER_HOVERED, None)
        ThemeRegistry._registry.pop(TAG_GLOBAL_THEME_SECTION_HEADER, None)
        dpg.destroy_context()


@pytest.fixture
def rendered_strip_padding(monkeypatch: pytest.MonkeyPatch) -> None:
    """Stand in for the layout pass so the strip reports the card's top padding without a viewport."""
    monkeypatch.setattr(dpg, "get_item_pos", lambda item: [0, _STRIP_PADDING])


def _glyphs() -> Glyphs:
    common = CommonGlyphs(
        tick=".",
        favorite="*",
        expanded=_EXPANDED_GLYPH,
        collapsed=_COLLAPSED_GLYPH,
        chevron_left=_CHEVRON_LEFT_GLYPH,
        chevron_right=_CHEVRON_RIGHT_GLYPH,
    )
    return Glyphs.model_construct(common=common)


def _controller(
    axis: CollapseAxis,
    initial_collapsed: bool = False,
    auto_height: bool = False,
    fill: bool = False,
) -> CollapseController:
    return CollapseController(
        _CARD_TAG,
        axis,
        expanded_height=_EXPANDED_HEIGHT,
        header_bar_height=_HEADER_BAR_HEIGHT,
        rail_width=_RAIL_WIDTH,
        glyphs=_glyphs(),
        initial_collapsed=initial_collapsed,
        auto_height=auto_height,
        fill=fill,
    )


def _build_card(controller: CollapseController) -> None:
    """Mirrors the item subtree ``_collapsible_section`` builds, without fonts or the header theme."""
    with dpg.window():
        with dpg.child_window(tag=controller.card_tag, height=_EXPANDED_HEIGHT):
            with dpg.child_window(tag=controller.strip_tag, height=_HEADER_BAR_HEIGHT, border=False):
                dpg.add_text(controller.chevron_glyph, tag=controller.chevron_tag)
            if controller.is_horizontal:
                with dpg.child_window(tag=controller.rail_tag, width=_RAIL_WIDTH, show=False):
                    dpg.add_text(".")
            controller.attach()
            with dpg.group(tag=controller.body_tag):
                dpg.add_text("body")
    controller.set_collapsed(controller.collapsed, notify=False)


class TestCollapseControllerAttach:
    """``attach`` wires the header bar for interaction. A child window rejects a clicked handler,
    so the toggle must ride a global mouse-click handler while only the hover handler binds to the
    strip; regressing to a bound clicked handler crashes the whole tab at build time."""

    def test_binds_hover_and_a_global_click_handler_without_error(self, dpg_context: None) -> None:
        controller = _controller(CollapseAxis.VERTICAL)
        _build_card(controller)

        assert dpg.does_item_exist(controller.strip_handler_tag)
        assert dpg.does_item_exist(controller.click_handler_tag)


class TestVerticalCollapse:
    """A vertical card shrinks to its header bar in place: collapsing hides the body and sets the
    card to a height that holds the strip plus its padding so the header always fits, and flips the
    chevron; expanding restores the fixed full height."""

    def test_collapsing_hides_the_body_and_shrinks_the_card_to_fit_the_strip(
        self, dpg_context: None, rendered_strip_padding: None
    ) -> None:
        controller = _controller(CollapseAxis.VERTICAL)
        _build_card(controller)

        controller.set_collapsed(True)

        assert dpg.get_item_configuration(controller.body_tag)["show"] is False
        assert dpg.get_item_configuration(controller.card_tag)["height"] == _HEADER_BAR_HEIGHT + 2 * _STRIP_PADDING
        assert dpg.get_item_configuration(controller.card_tag)["no_scrollbar"] is True
        assert dpg.get_value(controller.chevron_tag) == _COLLAPSED_GLYPH
        assert controller.collapsed_height == _HEADER_BAR_HEIGHT + 2 * _STRIP_PADDING

    def test_expanding_shows_the_body_and_restores_the_fixed_height(
        self, dpg_context: None, rendered_strip_padding: None
    ) -> None:
        controller = _controller(CollapseAxis.VERTICAL, initial_collapsed=True)
        _build_card(controller)

        controller.set_collapsed(False)

        assert dpg.get_item_configuration(controller.body_tag)["show"] is True
        assert dpg.get_item_configuration(controller.card_tag)["height"] == _EXPANDED_HEIGHT
        assert dpg.get_item_configuration(controller.card_tag)["no_scrollbar"] is False
        assert dpg.get_value(controller.chevron_tag) == _EXPANDED_GLYPH

    def test_builds_collapsed_when_seeded_collapsed(self, dpg_context: None, rendered_strip_padding: None) -> None:
        controller = _controller(CollapseAxis.VERTICAL, initial_collapsed=True)
        _build_card(controller)

        assert controller.collapsed is True
        assert dpg.get_item_configuration(controller.card_tag)["height"] == _HEADER_BAR_HEIGHT + 2 * _STRIP_PADDING
        assert dpg.get_value(controller.chevron_tag) == _COLLAPSED_GLYPH


class TestAutoHeightVerticalCollapse:
    """An auto-height card leaves its geometry to its own auto-resize: collapsing hides the body and
    flips the chevron without touching the card height, so the card settles onto the header bar on its
    own rather than being sized to a fixed collapsed bar."""

    def test_collapsing_hides_the_body_and_leaves_the_height_untouched(self, dpg_context: None) -> None:
        controller = _controller(CollapseAxis.VERTICAL, auto_height=True)
        _build_card(controller)

        controller.set_collapsed(True)

        assert dpg.get_item_configuration(controller.body_tag)["show"] is False
        assert dpg.get_item_configuration(controller.card_tag)["height"] == _EXPANDED_HEIGHT
        assert dpg.get_value(controller.chevron_tag) == _COLLAPSED_GLYPH

    def test_expanding_shows_the_body_and_leaves_the_height_untouched(self, dpg_context: None) -> None:
        controller = _controller(CollapseAxis.VERTICAL, initial_collapsed=True, auto_height=True)
        _build_card(controller)

        controller.set_collapsed(False)

        assert dpg.get_item_configuration(controller.body_tag)["show"] is True
        assert dpg.get_item_configuration(controller.card_tag)["height"] == _EXPANDED_HEIGHT
        assert dpg.get_value(controller.chevron_tag) == _EXPANDED_GLYPH


class TestFillVerticalCollapse:
    """A fill card fills its owner's reserved footprint while expanded and pins to its header bar while
    collapsed: collapsing hides the body and shrinks the card to the strip plus its padding, and expanding
    restores the fill sentinel height (0) so the card fills the reservation again. Pinning makes the
    collapsed size intrinsic, so the bar holds even when the owner is no longer reserving its footprint."""

    def test_collapsing_hides_the_body_and_pins_the_card_to_the_strip(
        self, dpg_context: None, rendered_strip_padding: None
    ) -> None:
        controller = _controller(CollapseAxis.VERTICAL, fill=True)
        _build_card(controller)

        controller.set_collapsed(True)

        assert dpg.get_item_configuration(controller.body_tag)["show"] is False
        assert dpg.get_item_configuration(controller.card_tag)["height"] == _HEADER_BAR_HEIGHT + 2 * _STRIP_PADDING
        assert dpg.get_item_configuration(controller.card_tag)["no_scrollbar"] is True
        assert dpg.get_value(controller.chevron_tag) == _COLLAPSED_GLYPH
        assert controller.collapsed_height == _HEADER_BAR_HEIGHT + 2 * _STRIP_PADDING

    def test_expanding_shows_the_body_and_restores_the_fill_height(
        self, dpg_context: None, rendered_strip_padding: None
    ) -> None:
        controller = _controller(CollapseAxis.VERTICAL, initial_collapsed=True, fill=True)
        _build_card(controller)

        controller.set_collapsed(False)

        assert dpg.get_item_configuration(controller.body_tag)["show"] is True
        assert dpg.get_item_configuration(controller.card_tag)["height"] == 0
        assert dpg.get_item_configuration(controller.card_tag)["no_scrollbar"] is False
        assert dpg.get_value(controller.chevron_tag) == _EXPANDED_GLYPH


class TestHorizontalCollapse:
    """A horizontal card leaves its own width to the coordinator: collapsing hides the body and the
    strip and reveals the rail, and the toggle is announced so the coordinator can reclaim the column."""

    def test_collapsing_swaps_the_strip_for_the_rail(self, dpg_context: None) -> None:
        controller = _controller(CollapseAxis.HORIZONTAL_LEFT)
        _build_card(controller)

        controller.set_collapsed(True)

        assert dpg.get_item_configuration(controller.body_tag)["show"] is False
        assert dpg.get_item_configuration(controller.strip_tag)["show"] is False
        assert dpg.get_item_configuration(controller.rail_tag)["show"] is True

    def test_hover_highlighting_covers_the_rail_as_well_as_the_strip(
        self, dpg_context: None, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A docked card highlights its rail on hover just as its strip, so both bars are hover-probed."""
        controller = _controller(CollapseAxis.HORIZONTAL_LEFT)
        _build_card(controller)
        probed: List[str] = []
        monkeypatch.setattr(dpg, "is_item_hovered", lambda tag: bool(probed.append(tag)) and False)

        controller._on_bar_hover()

        assert controller.strip_tag in probed
        assert controller.rail_tag in probed

    def test_toggle_announces_the_new_state(self, dpg_context: None) -> None:
        controller = _controller(CollapseAxis.HORIZONTAL_LEFT)
        _build_card(controller)
        announced: List[Tuple[str, bool]] = []
        controller.on_toggle = lambda card_tag, collapsed: announced.append((card_tag, collapsed))

        controller.toggle()
        controller.toggle()

        assert announced == [(_CARD_TAG, True), (_CARD_TAG, False)]

    def test_strip_chevron_points_at_the_dock_edge_and_the_rail_chevron_points_away(self) -> None:
        """The strip (shown while expanded) points at the dock edge; the rail (shown while collapsed) the other way.

        Each affordance shows in only one state, so neither flips: clicking the strip collapses the card toward
        its edge, and clicking the rail expands it back out the other way.
        """
        left = _controller(CollapseAxis.HORIZONTAL_LEFT)
        right = _controller(CollapseAxis.HORIZONTAL_RIGHT)

        assert left.chevron_glyph == _CHEVRON_LEFT_GLYPH
        assert left.rail_chevron_glyph == _CHEVRON_RIGHT_GLYPH
        assert right.chevron_glyph == _CHEVRON_RIGHT_GLYPH
        assert right.rail_chevron_glyph == _CHEVRON_LEFT_GLYPH

        assert _controller(CollapseAxis.HORIZONTAL_LEFT, initial_collapsed=True).chevron_glyph == _CHEVRON_LEFT_GLYPH
        assert _controller(CollapseAxis.HORIZONTAL_RIGHT, initial_collapsed=True).chevron_glyph == _CHEVRON_RIGHT_GLYPH


_RAIL_LABEL = "Filesystem"
_RAIL_GLYPH = "#"


class _RailPanel(GUIPanel):
    """A bare panel that only exists to build ``_collapsible_section`` so its rail can be inspected."""

    def create_panel(self, parent: str) -> None:
        raise NotImplementedError


@pytest.fixture
def section_panel(dpg_context: None, monkeypatch: pytest.MonkeyPatch) -> _RailPanel:
    """A horizontally docked panel wired with test geometry, its fonts and text metrics stubbed out.

    Without a viewport the font atlas never builds, so rail centering only has to defer cleanly rather
    than measure: the font lookups return a sentinel and ``get_text_size`` reads back None.
    """
    monkeypatch.setattr(FontRegistry, "bind_to_item", staticmethod(lambda item, font: None))
    monkeypatch.setattr(FontRegistry, "get_tag", classmethod(lambda cls, font: 0))
    monkeypatch.setattr(dpg, "get_text_size", lambda text, font=0: None)
    GUIPanel.configure_section_header(
        _glyphs(),
        SectionHeaderLayout(glyph=GlyphLayout(indent=0, width=_RAIL_WIDTH), chevron_offset=8),
        CollapseLayout(header_bar_height=_HEADER_BAR_HEIGHT, rail_width=_RAIL_WIDTH, rail_title_gap=6),
    )
    panel = _RailPanel(tag=_CARD_TAG)
    panel._enable_horizontal_collapse(initial_collapsed=True, side=CollapseAxis.HORIZONTAL_LEFT)
    return panel


class TestHorizontalRailTitle:
    """A docked card's rail names itself: it stacks the card title one uppercased character per line,
    matching the header's treatment, so a collapsed column still reads as what it holds."""

    def test_rail_stacks_the_uppercased_title_one_character_per_line(self, section_panel: _RailPanel) -> None:
        with dpg.window():
            with dpg.child_window(tag=section_panel.tag):
                with section_panel._collapsible_section(_RAIL_LABEL, glyph=_RAIL_GLYPH):
                    dpg.add_text("body")

        controller = section_panel.collapse
        assert controller is not None
        (rail_content,) = dpg.get_item_children(controller.rail_tag, 1)
        rail_texts = [dpg.get_value(item) for item in dpg.get_item_children(rail_content, 1)]
        assert "\n".join(_RAIL_LABEL.upper()) in rail_texts
