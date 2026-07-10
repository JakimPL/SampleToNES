from abc import ABC, abstractmethod
from typing import Optional

import dearpygui.dearpygui as dpg

from sampletones_application.layout.glyphs import GlyphLayout, Glyphs
from sampletones_application.tags.general import TAG_GLOBAL_THEME_SECTION_HEADER
from sampletones_application.ui.elements.fonts.font import Font
from sampletones_application.ui.elements.fonts.registry import FontRegistry
from sampletones_application.ui.themes.registry import ThemeRegistry
from sampletones_application.utils.gui.dpg import dpg_configure_item
from sampletones_shared.types.application import Sender
from sampletones_shared.utils.callbacks import CallbackMixin


class GUIPanel(CallbackMixin, ABC):
    """
    The foundation of every visible component in the View layer.

    - State flows in through ``update_view``; user actions flow out through
      ``on_x`` callback hooks.
    - A panel owns its widget subtree and holds no domain state — it knows
      how to display data, not what it means.
    """

    _glyphs: Glyphs
    _glyph_layout: GlyphLayout

    def __init__(
        self,
        tag: str,
        width: int = 0,
        height: int = 0,
    ) -> None:
        self.tag = tag
        self.width = width
        self.height = height

    @abstractmethod
    def create_panel(self, parent: str) -> None: ...

    @classmethod
    def configure_section_header(
        cls,
        glyphs: Glyphs,
        glyph_layout: GlyphLayout,
    ) -> None:
        """Set the shared glyph palette and the fixed marker width for every section header, from config."""
        cls._glyphs = glyphs
        cls._glyph_layout = glyph_layout

    def _create_section_header(
        self,
        label: str,
        *,
        glyph: Optional[str] = None,
        parent: Sender = 0,
        tag: Sender = 0,
    ) -> None:
        """Render this panel's section header: a compact accent-toned label with a leading marker.

        The marker is a purpose glyph when ``glyph`` is given, otherwise the shared accent tick,
        so a header can signal what its card is for while headers without a glyph stay uniform.
        A fixed-width marker column keeps the label starting at the same offset regardless of the
        glyph's own width. Every panel opens with the same header treatment, so defining it on the
        base keeps the tabs consistent and gives one place to restyle every header at once. ``parent``
        targets a specific container for panels that build outside a ``with`` block.
        """
        theme = ThemeRegistry.get(TAG_GLOBAL_THEME_SECTION_HEADER)
        marker_glyph = glyph if glyph is not None else self._glyphs.common.tick
        with dpg.group(parent=parent, tag=tag) as header:
            with dpg.table(
                header_row=False,
                policy=dpg.mvTable_SizingFixedFit,
                resizable=False,
            ):
                dpg.add_table_column(
                    width_fixed=True,
                    init_width_or_weight=self._glyph_layout.width,
                )
                dpg.add_table_column(width_fixed=True)
                with dpg.table_row():
                    with dpg.table_cell():
                        marker = dpg.add_text(marker_glyph, indent=self._glyph_layout.indent)
                        FontRegistry.bind_to_item(marker, Font.ICON)

                    with dpg.table_cell():
                        label_text = dpg.add_text(label.upper())
                        FontRegistry.bind_to_item(label_text, Font.BOLD)

        dpg.add_separator()
        theme.bind_to_item(header)

    def set_visibility(self, visible: bool) -> None:
        dpg_configure_item(self.tag, show=visible)

    def show(self) -> None:
        self.set_visibility(True)

    def hide(self) -> None:
        self.set_visibility(False)
