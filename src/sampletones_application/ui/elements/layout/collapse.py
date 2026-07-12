from enum import Enum, auto
from typing import Callable, Optional

import dearpygui.dearpygui as dpg

from sampletones_application.constants.global_ import TAG_SEPARATOR
from sampletones_application.layout.glyphs import Glyphs
from sampletones_application.tags.general import (
    SUF_COLLAPSE_BODY,
    SUF_COLLAPSE_CHEVRON,
    SUF_COLLAPSE_RAIL,
    SUF_COLLAPSE_STRIP,
    SUF_HANDLER_REGISTRY,
    TAG_GLOBAL_THEME_COLLAPSE_HEADER,
    TAG_GLOBAL_THEME_COLLAPSE_HEADER_HOVERED,
)
from sampletones_application.ui.themes.registry import ThemeRegistry
from sampletones_application.utils.gui.dpg import (
    dpg_configure_item,
    dpg_delete_item,
    dpg_set_value,
)
from sampletones_application.utils.gui.frame import FrameCallbackManager
from sampletones_shared.utils.callbacks import CallbackMixin


class CollapseAxis(Enum):
    VERTICAL = auto()
    HORIZONTAL_LEFT = auto()
    HORIZONTAL_RIGHT = auto()


class CollapseController(CallbackMixin):
    """Drives one card's collapse interaction and, for a vertical card, its geometry.

    A vertical card owns its own height, so this controller shrinks it to the header
    bar in place. A card that sizes itself to its content (``auto_height``) collapses by
    hiding its body alone, letting the card's own auto-resize settle onto the header bar.
    A ``fill`` card leaves its height to the owner that reserves its footprint, so it too
    collapses by hiding its body alone and shrinks as the owner shrinks the reservation.
    A horizontal card only hides its body and swaps in a rail; the owning coordinator
    reclaims the freed width, which it learns through ``on_toggle``. The card's tag is the
    persistence key, so the collapsible set is defined by which panels build a controller
    rather than by a central registry.
    """

    def __init__(
        self,
        card_tag: str,
        axis: CollapseAxis,
        *,
        expanded_height: int,
        header_bar_height: int,
        rail_width: int,
        glyphs: Glyphs,
        initial_collapsed: bool = False,
        auto_height: bool = False,
        fill: bool = False,
    ) -> None:
        self.card_tag = card_tag
        self.axis = axis
        self._expanded_height = expanded_height
        self._header_bar_height = header_bar_height
        self._rail_width = rail_width
        self._glyphs = glyphs
        self._collapsed = initial_collapsed
        self._auto_height = auto_height
        self._fill = fill

        self.strip_tag = f"{card_tag}{SUF_COLLAPSE_STRIP}"
        self.body_tag = f"{card_tag}{SUF_COLLAPSE_BODY}"
        self.rail_tag = f"{card_tag}{SUF_COLLAPSE_RAIL}"
        self.chevron_tag = f"{card_tag}{SUF_COLLAPSE_CHEVRON}"
        self.strip_handler_tag = f"{self.strip_tag}{SUF_HANDLER_REGISTRY}"
        self.click_handler_tag = f"{card_tag}{SUF_COLLAPSE_STRIP}{TAG_SEPARATOR}click{SUF_HANDLER_REGISTRY}"

        self.on_toggle: Optional[Callable[[str, bool], None]] = None
        self._collapsed_height: Optional[int] = None

    @property
    def collapsed(self) -> bool:
        return self._collapsed

    @property
    def expanded_height(self) -> int:
        return self._expanded_height

    @property
    def collapsed_height(self) -> Optional[int]:
        """The card's measured height while collapsed to its header bar, once the strip has rendered.

        Reads as ``None`` until the strip lays out, since the bar height derives from the rendered
        strip offset. A coordinator that reserves space for a collapsed sibling waits for a value.
        """
        return self._collapsed_height

    def set_expanded_height(self, height: int) -> None:
        """Retune the height the card returns to when expanded, applying it live for an expanded vertical card."""
        self._expanded_height = height
        if not self._collapsed and self.axis is CollapseAxis.VERTICAL and self._manages_height:
            dpg_configure_item(self.card_tag, height=height)

    @property
    def auto_height(self) -> bool:
        return self._auto_height

    @property
    def _manages_height(self) -> bool:
        """Whether this controller sets the card's height directly.

        A plain vertical card is shrunk to a fixed bar on collapse. A card that auto-resizes to
        its content, or one that fills a footprint its owner reserves, leaves its height alone —
        it settles by its own resize or by the owner shrinking the reservation.
        """
        return not self._auto_height and not self._fill

    @property
    def header_bar_height(self) -> int:
        return self._header_bar_height

    @property
    def rail_width(self) -> int:
        return self._rail_width

    @property
    def is_horizontal(self) -> bool:
        return self.axis is not CollapseAxis.VERTICAL

    @property
    def chevron_glyph(self) -> str:
        """The strip's affordance glyph, pointing toward the collapse direction for the card's axis.

        A docked card's strip only shows while expanded and collapsing pulls it toward its dock edge,
        so a horizontal strip points at that edge and never flips. A vertical strip stays in place, so
        it flips between the expanded and collapsed markers with the state.
        """
        if self.axis is CollapseAxis.HORIZONTAL_LEFT:
            return self._glyphs.common.chevron_left

        if self.axis is CollapseAxis.HORIZONTAL_RIGHT:
            return self._glyphs.common.chevron_right

        return self._glyphs.common.collapsed if self._collapsed else self._glyphs.common.expanded

    @property
    def rail_chevron_glyph(self) -> str:
        """The rail's affordance glyph, shown while collapsed and pointing toward the expand direction.

        The rail only shows while collapsed, so a click expands the card away from its dock edge; the
        chevron points that way, opposite the strip's.
        """
        if self.axis is CollapseAxis.HORIZONTAL_RIGHT:
            return self._glyphs.common.chevron_left

        return self._glyphs.common.chevron_right

    def attach(self) -> None:
        """Binds hover-to-highlight to the header strip and a global click that toggles whichever bar is hovered.

        A child window accepts a hover handler but not a clicked handler, so the toggle rides a global
        mouse-click handler gated on the strip or rail being hovered.
        """
        dpg_delete_item(self.strip_handler_tag)
        with dpg.item_handler_registry(tag=self.strip_handler_tag):
            dpg.add_item_hover_handler(callback=self._on_strip_hover)

        dpg.bind_item_handler_registry(self.strip_tag, self.strip_handler_tag)
        self._bind_idle_theme()

        dpg_delete_item(self.click_handler_tag)
        with dpg.handler_registry(tag=self.click_handler_tag):
            dpg.add_mouse_click_handler(button=dpg.mvMouseButton_Left, callback=self._on_mouse_click)

    def set_collapsed(self, collapsed: bool, *, notify: bool = True) -> None:
        self._collapsed = collapsed
        dpg_configure_item(self.body_tag, show=not collapsed)

        if self.is_horizontal:
            dpg_configure_item(self.strip_tag, show=not collapsed)
            dpg_configure_item(self.rail_tag, show=collapsed)
        elif self._manages_height:
            if collapsed:
                self._apply_collapsed_height()
            else:
                dpg_configure_item(
                    self.card_tag,
                    height=self._expanded_height,
                    no_scrollbar=False,
                    no_scroll_with_mouse=False,
                )

        dpg_set_value(self.chevron_tag, self.chevron_glyph)

        if notify:
            self.call(self.on_toggle, self.card_tag, collapsed)

    def _apply_collapsed_height(self) -> None:
        """Shrink the card to a bar tall enough to hold the header strip plus the card's own padding.

        The padding is read from the rendered strip's top offset so the bar matches the card theme.
        Before the strip has rendered, the sizing waits a frame until that offset becomes available.
        """
        if not self._collapsed:
            return

        if self._collapsed_height is None:
            strip_offset = self._strip_top_offset()
            if strip_offset is None:
                FrameCallbackManager.set_frame_callback(self._apply_collapsed_height)
                return
            self._collapsed_height = self._header_bar_height + 2 * strip_offset

        dpg_configure_item(
            self.card_tag,
            height=self._collapsed_height,
            no_scrollbar=True,
            no_scroll_with_mouse=True,
        )

    def _strip_top_offset(self) -> Optional[int]:
        """The strip's vertical offset inside the card once rendered, standing in for the card padding.

        The offset settles to the card's top padding only after the strip has been laid out, so a
        non-positive reading means the card has yet to render and the caller should wait a frame.
        """
        if not dpg.does_item_exist(self.strip_tag):
            return None
        offset = int(dpg.get_item_pos(self.strip_tag)[1])
        if offset <= 0:
            return None
        return offset

    def toggle(self) -> None:
        self.set_collapsed(not self._collapsed)

    def _on_mouse_click(self) -> None:
        if self._is_bar_hovered():
            self.toggle()

    def _is_bar_hovered(self) -> bool:
        if dpg.does_item_exist(self.strip_tag) and dpg.is_item_hovered(self.strip_tag):
            return True

        return bool(self.is_horizontal and dpg.does_item_exist(self.rail_tag) and dpg.is_item_hovered(self.rail_tag))

    def _on_strip_hover(self) -> None:
        if not dpg.does_item_exist(self.strip_tag):
            return

        if dpg.is_item_hovered(self.strip_tag):
            self._bind_hovered_theme()
            FrameCallbackManager.set_frame_callback(self._on_strip_hover, 2)
        else:
            self._bind_idle_theme()

    def _bind_idle_theme(self) -> None:
        ThemeRegistry.get(TAG_GLOBAL_THEME_COLLAPSE_HEADER).bind_to_item(self.strip_tag)

    def _bind_hovered_theme(self) -> None:
        ThemeRegistry.get(TAG_GLOBAL_THEME_COLLAPSE_HEADER_HOVERED).bind_to_item(self.strip_tag)
