from enum import Enum, auto
from typing import Callable, Optional

import dearpygui.dearpygui as dpg

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
    bar in place. A horizontal card only hides its body and swaps in a rail; the owning
    coordinator reclaims the freed width, which it learns through ``on_toggle``. The
    card's tag is the persistence key, so the collapsible set is defined by which panels
    build a controller rather than by a central registry.
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
    ) -> None:
        self.card_tag = card_tag
        self.axis = axis
        self._expanded_height = expanded_height
        self._header_bar_height = header_bar_height
        self._rail_width = rail_width
        self._glyphs = glyphs
        self._collapsed = initial_collapsed

        self.strip_tag = f"{card_tag}{SUF_COLLAPSE_STRIP}"
        self.body_tag = f"{card_tag}{SUF_COLLAPSE_BODY}"
        self.rail_tag = f"{card_tag}{SUF_COLLAPSE_RAIL}"
        self.chevron_tag = f"{card_tag}{SUF_COLLAPSE_CHEVRON}"
        self.strip_handler_tag = f"{self.strip_tag}{SUF_HANDLER_REGISTRY}"
        self.rail_handler_tag = f"{self.rail_tag}{SUF_HANDLER_REGISTRY}"

        self.on_toggle: Optional[Callable[[str, bool], None]] = None

    @property
    def collapsed(self) -> bool:
        return self._collapsed

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
        if self._collapsed:
            return self._glyphs.common.collapsed
        return self._glyphs.common.expanded

    def attach(self) -> None:
        """Binds click-to-toggle and hover-to-highlight to the built header strip and rail."""
        dpg_delete_item(self.strip_handler_tag)
        with dpg.item_handler_registry(tag=self.strip_handler_tag):
            dpg.add_item_clicked_handler(callback=self._on_toggle_clicked)
            dpg.add_item_hover_handler(callback=self._on_strip_hover)

        dpg.bind_item_handler_registry(self.strip_tag, self.strip_handler_tag)
        self._bind_idle_theme()

        if self.is_horizontal:
            dpg_delete_item(self.rail_handler_tag)
            with dpg.item_handler_registry(tag=self.rail_handler_tag):
                dpg.add_item_clicked_handler(callback=self._on_toggle_clicked)

            dpg.bind_item_handler_registry(self.rail_tag, self.rail_handler_tag)

    def set_collapsed(self, collapsed: bool, *, notify: bool = True) -> None:
        self._collapsed = collapsed
        dpg_configure_item(self.body_tag, show=not collapsed)

        if self.is_horizontal:
            dpg_configure_item(self.strip_tag, show=not collapsed)
            dpg_configure_item(self.rail_tag, show=collapsed)
        else:
            height = self._header_bar_height if collapsed else self._expanded_height
            dpg_configure_item(self.card_tag, height=height)

        dpg_set_value(self.chevron_tag, self.chevron_glyph)

        if notify:
            self.call(self.on_toggle, self.card_tag, collapsed)

    def toggle(self) -> None:
        self.set_collapsed(not self._collapsed)

    def _on_toggle_clicked(self) -> None:
        self.toggle()

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
