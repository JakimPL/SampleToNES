from abc import ABC, abstractmethod
from contextlib import contextmanager
from functools import partial
from typing import Callable, Iterator, List, Optional, Tuple

import dearpygui.dearpygui as dpg

from sampletones_application.layout.general import CollapseLayout
from sampletones_application.layout.glyphs import GlyphLayout, Glyphs
from sampletones_application.tags.general import TAG_GLOBAL_THEME_SECTION_HEADER
from sampletones_application.ui.elements.fonts.font import Font
from sampletones_application.ui.elements.fonts.registry import FontRegistry
from sampletones_application.ui.elements.layout.card import card
from sampletones_application.ui.elements.layout.collapse import (
    CollapseAxis,
    CollapseController,
)
from sampletones_application.ui.themes.registry import ThemeRegistry
from sampletones_application.utils.gui.dpg import dpg_configure_item
from sampletones_application.utils.gui.frame import FrameCallbackManager
from sampletones_shared.types.application import Sender
from sampletones_shared.utils.callbacks import CallbackMixin

# The rail child-window's inner padding, mirroring the theme WindowPadding it inherits; rail items
# are centered within the content region this padding leaves, so it must track that style.
_RAIL_CONTENT_PADDING = 8


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
    _collapse_layout: CollapseLayout

    def __init__(
        self,
        tag: str,
        width: int = 0,
        height: int = 0,
    ) -> None:
        self.tag = tag
        self.width = width
        self.height = height
        self._collapse: Optional[CollapseController] = None

    @abstractmethod
    def create_panel(self, parent: str) -> None: ...

    @property
    def collapse(self) -> Optional[CollapseController]:
        return self._collapse

    @property
    def collapsed(self) -> bool:
        return self._collapse is not None and self._collapse.collapsed

    @property
    def _body_container(self) -> str:
        """The container new body content attaches to: the collapse body group when collapsible, else the card.

        A collapsible card hides its body group to collapse, so content built with an explicit parent
        must target that group rather than the card, or it stays visible when the card collapses.
        """
        if self._collapse is not None:
            return self._collapse.body_tag
        return self.tag

    @classmethod
    def configure_section_header(
        cls,
        glyphs: Glyphs,
        glyph_layout: GlyphLayout,
        collapse_layout: CollapseLayout,
    ) -> None:
        """Set the glyph palette, marker width, and collapse geometry every section header draws from."""
        cls._glyphs = glyphs
        cls._glyph_layout = glyph_layout
        cls._collapse_layout = collapse_layout

    def _enable_vertical_collapse(
        self,
        *,
        initial_collapsed: bool,
        auto_height: bool = False,
        fill: bool = False,
        card_tag: Optional[str] = None,
    ) -> None:
        """Give this card a controller that shrinks it to a header bar in place, seeded from persisted state.

        ``auto_height`` suits a card that sizes itself to its content: it collapses by hiding its body
        and lets its own auto-resize settle onto the header bar. ``fill`` suits a card whose footprint is
        reserved by an owning coordinator: it collapses by hiding its body alone and shrinks as the owner
        shrinks the reservation, so the collapsed bar sits flush with no space to predict. ``card_tag``
        names the child-window the controller resizes when it differs from the panel tag, so a panel whose
        card wraps an inner group still collapses the outer card.
        """
        self._collapse = CollapseController(
            card_tag if card_tag is not None else self.tag,
            CollapseAxis.VERTICAL,
            expanded_height=self.height,
            header_bar_height=self._collapse_layout.header_bar_height,
            rail_width=self._collapse_layout.rail_width,
            glyphs=self._glyphs,
            initial_collapsed=initial_collapsed,
            auto_height=auto_height,
            fill=fill,
        )

    def _enable_horizontal_collapse(
        self,
        *,
        initial_collapsed: bool,
        side: CollapseAxis,
    ) -> None:
        """Give this panel a controller that swaps its body for a narrow rail, freeing the width for its coordinator.

        ``side`` names the edge the panel docks against, orienting the affordance toward the collapse direction;
        it must be ``HORIZONTAL_LEFT`` or ``HORIZONTAL_RIGHT``. A docked card owns none of its own geometry: it
        hides its body and shows the rail, leaving the freed width for the coordinator to reclaim on the toggle.
        """
        if side is CollapseAxis.VERTICAL:
            raise ValueError(f"Card {self.tag} enabled horizontal collapse with a vertical axis.")

        self._collapse = CollapseController(
            self.tag,
            side,
            expanded_height=self.height,
            header_bar_height=self._collapse_layout.header_bar_height,
            rail_width=self._collapse_layout.rail_width,
            glyphs=self._glyphs,
            initial_collapsed=initial_collapsed,
        )

    def set_collapse_handler(self, callback: Callable[[str, bool], None]) -> None:
        """Route this card's collapse toggles to ``callback`` so the coordinator can persist and react to them."""
        if self._collapse is not None:
            self._collapse.on_toggle = callback

    def set_expanded_height(self, height: int) -> None:
        """Change the height this card returns to when expanded, applying it now while the card is expanded.

        A coordinator uses this to retune one fixed-height card when a sibling's collapse frees space.
        """
        self.height = height
        if self._collapse is not None:
            self._collapse.set_expanded_height(height)

    def _create_section_header(
        self,
        label: str,
        *,
        glyph: Optional[str] = None,
        parent: Sender = 0,
        tag: Sender = 0,
        affordance: Optional[str] = None,
        affordance_tag: Sender = 0,
    ) -> None:
        """Render this panel's section header: a compact accent-toned label with a leading marker.

        The marker is a purpose glyph when ``glyph`` is given, otherwise the shared accent tick,
        so a header can signal what its card is for while headers without a glyph stay uniform.
        A fixed-width marker column keeps the label starting at the same offset regardless of the
        glyph's own width. Every panel opens with the same header treatment, so defining it on the
        base keeps the tabs consistent and gives one place to restyle every header at once. ``parent``
        targets a specific container for panels that build outside a ``with`` block.

        When ``affordance`` is given, a stretch spacer pushes a right-aligned chevron to the header's
        end, signalling the card collapses; the chevron carries ``affordance_tag`` so the controller
        can flip its glyph, and the trailing separator is dropped because the collapse strip frames the
        header itself.
        """
        theme = ThemeRegistry.get(TAG_GLOBAL_THEME_SECTION_HEADER)
        marker_glyph = glyph if glyph is not None else self._glyphs.common.tick
        collapsible = affordance is not None
        policy = dpg.mvTable_SizingStretchProp if collapsible else dpg.mvTable_SizingFixedFit
        with dpg.group(parent=parent, tag=tag) as header:
            with dpg.table(header_row=False, policy=policy, resizable=False):
                dpg.add_table_column(
                    width_fixed=True,
                    init_width_or_weight=self._glyph_layout.width,
                )
                dpg.add_table_column(width_fixed=not collapsible)
                if collapsible:
                    dpg.add_table_column(width_fixed=True)

                with dpg.table_row():
                    with dpg.table_cell():
                        marker = dpg.add_text(marker_glyph, indent=self._glyph_layout.indent)
                        FontRegistry.bind_to_item(marker, Font.ICON)

                    with dpg.table_cell():
                        label_text = dpg.add_text(label.upper())
                        FontRegistry.bind_to_item(label_text, Font.BOLD)

                    if collapsible:
                        with dpg.table_cell():
                            chevron = dpg.add_text(affordance, tag=affordance_tag)
                            FontRegistry.bind_to_item(chevron, Font.ICON)

        if not collapsible:
            dpg.add_separator()

        theme.bind_to_item(header)

    @contextmanager
    def _collapsible_card(
        self,
        parent: str,
        label: str,
        *,
        glyph: str,
        width: int = -1,
        no_scrollbar: bool = False,
        show: bool = True,
    ) -> Iterator[None]:
        """Open this panel's card and frame its content with the collapsible header in one step.

        The card's tag, height, and auto-resize follow the collapse controller, so the card and its
        controller stay in step; the panel supplies only the width, scrollbar, and initial visibility
        the controller does not own. A controller must be enabled first via ``_enable_vertical_collapse``.
        """
        controller = self._collapse
        if controller is None:
            raise RuntimeError(f"Card {self.tag} opened a collapsible card without a collapse controller.")

        with card(
            parent,
            controller.card_tag,
            width=width,
            height=controller.expanded_height,
            auto_resize_y=controller.auto_height,
            no_scrollbar=no_scrollbar,
            show=show,
        ):
            with self._collapsible_section(label, glyph=glyph):
                yield

    @contextmanager
    def _collapsible_section(
        self,
        label: str,
        *,
        glyph: str,
    ) -> Iterator[None]:
        """Frame a card's content with a clickable, collapsible header and yield its body container.

        The header lives in a thin child-window strip so it can carry a hover background, and its
        chevron signals the card collapses. The body opens as a group tagged for show/hide, so the
        panel's existing flat ``dpg.add_*`` calls land inside it unchanged. Horizontal cards also get
        a hidden rail the collapsed state swaps in, carrying the card's glyph, an expand chevron, and
        the title stacked one character per line in the header's accent style so the collapsed column
        still names itself. Building finishes by applying the persisted collapsed state without
        re-notifying, so restore-on-launch matches the stored value. The card must have a controller
        enabled first, so ``_enable_vertical_collapse`` (or a horizontal equivalent) runs in the
        panel's constructor.
        """
        controller = self._collapse
        if controller is None:
            raise RuntimeError(f"Card {self.tag} opened a collapsible section without a collapse controller.")

        with dpg.child_window(
            tag=controller.strip_tag,
            height=controller.header_bar_height,
            border=False,
            no_scrollbar=True,
        ):
            self._create_section_header(
                label,
                glyph=glyph,
                affordance=controller.chevron_glyph,
                affordance_tag=controller.chevron_tag,
            )

        if controller.is_horizontal:
            with dpg.child_window(
                tag=controller.rail_tag,
                width=-1,
                border=False,
                no_scrollbar=True,
                show=False,
            ):
                with dpg.group() as rail_content:
                    rail_chevron = dpg.add_text(controller.rail_chevron_glyph)
                    FontRegistry.bind_to_item(rail_chevron, Font.ICON)
                    rail_marker = dpg.add_text(glyph)
                    FontRegistry.bind_to_item(rail_marker, Font.ICON)
                    dpg.add_spacer(height=self._collapse_layout.rail_title_gap)
                    rail_title = dpg.add_text("\n".join(label.upper()))
                    FontRegistry.bind_to_item(rail_title, Font.MONO_BOLD_SMALL)
                ThemeRegistry.get(TAG_GLOBAL_THEME_SECTION_HEADER).bind_to_item(rail_content)
                self._center_rail_items(
                    controller.rail_width,
                    [
                        (rail_chevron, Font.ICON),
                        (rail_marker, Font.ICON),
                        (rail_title, Font.MONO_BOLD_SMALL),
                    ],
                )

        controller.attach()

        with dpg.group(tag=controller.body_tag):
            yield

        controller.set_collapsed(controller.collapsed, notify=False)

    def _center_rail_items(self, rail_width: int, items: List[Tuple[Sender, Font]]) -> None:
        """Indent each rail item so its glyph sits centered in the rail's content region.

        Text is left-aligned, so an item is nudged right by half the slack between the content width
        and the glyph's own width — the chevron, card glyph, and every title character each get their
        own offset. ``get_text_size`` reads back ``None`` until the font atlas is built a frame in, so
        the pass reschedules itself until it can measure.
        """
        content_width = rail_width - 2 * _RAIL_CONTENT_PADDING
        indents: List[Tuple[Sender, int]] = []
        for item, font in items:
            size = dpg.get_text_size(dpg.get_value(item), font=FontRegistry.get_tag(font))
            if size is None:
                FrameCallbackManager.set_frame_callback(partial(self._center_rail_items, rail_width, items))
                return
            indents.append((item, max(0, round((content_width - size[0]) / 2))))

        for item, indent in indents:
            dpg_configure_item(item, indent=indent)

    def set_visibility(self, visible: bool) -> None:
        dpg_configure_item(self.tag, show=visible)

    def show(self) -> None:
        self.set_visibility(True)

    def hide(self) -> None:
        self.set_visibility(False)
