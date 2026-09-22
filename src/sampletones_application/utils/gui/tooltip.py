from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

import dearpygui.dearpygui as dpg

from sampletones_application.tags.general import (
    TAG_GLOBAL_THEME_TOOLTIP,
    TAG_GLOBAL_THEME_TOOLTIP_TABLE,
)
from sampletones_application.ui.elements.fonts.font import Font
from sampletones_application.ui.elements.fonts.registry import FontRegistry
from sampletones_application.ui.themes.registry import ThemeRegistry
from sampletones_application.utils.gui.palette.dpg import dpg_set_palette_color
from sampletones_application.utils.palette.colors.base import BaseColor
from sampletones_shared.types.application import Sender
from sampletones_shared.types.data import SerializedData


@dataclass(frozen=True)
class DetailSwatch:
    """One thing a hover lists, named and marked in the color that thing is drawn in elsewhere."""

    name: str
    color: BaseColor


def show_tooltip(
    parent: Sender,
    message: str,
    *,
    tag: Optional[str] = None,
    text_tag: Optional[str] = None,
) -> Sender:
    """Attaches a hover explanation to ``parent``, named by its tag or by the id it was created with.

    ``text_tag`` names the message itself, which is what a caller gives it where the explanation
    changes while the widget it explains stands.
    """
    tooltip_kwargs: SerializedData = {"hide_on_activity": True}
    if tag is not None:
        tooltip_kwargs["tag"] = tag

    text_kwargs: SerializedData = {}
    if text_tag is not None:
        text_kwargs["tag"] = text_tag

    with dpg.tooltip(parent, **tooltip_kwargs) as tooltip:
        ThemeRegistry.get(TAG_GLOBAL_THEME_TOOLTIP).bind_to_item(tooltip)
        tooltip_text: Sender = dpg.add_text(message, **text_kwargs)
        FontRegistry.bind_to_item(tooltip_text, Font.REGULAR_SMALL)

    return tooltip_text


def set_tooltip_visible(tag: str, visible: bool) -> None:
    """Shows or hides a tooltip along with the widget it explains.

    DearPyGui keeps a tooltip live over the rectangle its parent last drew at, so a tooltip left
    showing while its widget is hidden explains whatever moved into that place. Toggling the two
    together keeps an explanation on the control it belongs to.
    """
    if dpg.does_item_exist(tag):
        dpg.configure_item(tag, show=visible)


def attach_disabled_tooltip(
    parent: str,
    message: str,
    *,
    tag: str,
) -> None:
    """Attaches an explanatory tooltip to ``parent`` — an enabled group wrapping a control that can be
    disabled — and hides it by default. Toggle ``tag``'s ``show`` to reveal the explanation while the
    control is unavailable. The wrapper group is the hover target because DearPyGui surfaces a tooltip
    for an enabled item, so the explanation reaches the user even when the inner control is disabled."""
    with dpg.tooltip(parent, tag=tag, show=False, hide_on_activity=True) as tooltip:
        ThemeRegistry.get(TAG_GLOBAL_THEME_TOOLTIP).bind_to_item(tooltip)
        tooltip_text = dpg.add_text(message)
        FontRegistry.bind_to_item(tooltip_text, Font.REGULAR_SMALL)


def create_detail_tooltip(parent: str, *, tag: str) -> None:
    """Creates a hidden detail tooltip bound to ``parent``.

    The tooltip starts hidden and the tree reveals it by toggling its ``show`` from the precise
    per-node hover handler, so the details stay tied to the owning node's own row while the pointer
    explores that node's expanded descendants.
    """
    with dpg.tooltip(parent, tag=tag, show=False):
        ThemeRegistry.get(TAG_GLOBAL_THEME_TOOLTIP).bind_to_item(tag)


def populate_detail_tooltip(
    tag: str,
    items: List[Tuple[str, str]],
    *,
    swatch_glyph: str,
    swatch_label: str,
    swatches: Sequence[DetailSwatch],
) -> None:
    """Replaces the tooltip's content with ``label``/``value`` pairs and the list that follows them.

    ``mvTable_SizingFixedFit`` sizes each column to its own content, so the label column tracks its
    own text width independently of the value column. A compact theme tightens the row padding.
    The list below the pairs reads under ``swatch_label``, one row per thing, each marked with
    ``swatch_glyph`` in that thing's own color. A tooltip given nothing to list shows the pairs
    alone.
    """
    dpg.delete_item(tag, children_only=True)
    if items:
        _add_detail_table(tag, items)

    if not swatches:
        return

    if items:
        dpg.add_separator(parent=tag)

    _add_swatch_list(tag, swatch_glyph, swatch_label, swatches)


def _add_detail_table(tag: str, items: List[Tuple[str, str]]) -> None:
    with dpg.table(
        parent=tag,
        header_row=False,
        policy=dpg.mvTable_SizingFixedFit,
        borders_innerH=False,
        borders_innerV=False,
        borders_outerH=False,
        borders_outerV=False,
    ) as table:
        ThemeRegistry.get(TAG_GLOBAL_THEME_TOOLTIP_TABLE).bind_to_item(table)
        dpg.add_table_column()
        dpg.add_table_column()
        for label, value in items:
            with dpg.table_row():
                label_text = dpg.add_text(label)
                FontRegistry.bind_to_item(label_text, Font.REGULAR_SMALL)
                value_text = dpg.add_text(value)
                FontRegistry.bind_to_item(value_text, Font.MONO_SMALL)


def _add_swatch_list(
    tag: str,
    glyph: str,
    label: str,
    swatches: Sequence[DetailSwatch],
) -> None:
    """Lists each thing under its heading, the mark ahead of the name reading in the thing's color."""
    heading = dpg.add_text(label, parent=tag)
    FontRegistry.bind_to_item(heading, Font.REGULAR_SMALL)
    for swatch in swatches:
        with dpg.group(horizontal=True, parent=tag):
            mark = dpg.add_text(glyph)
            dpg_set_palette_color(mark, swatch.color)
            FontRegistry.bind_to_item(mark, Font.ICON)
            name = dpg.add_text(swatch.name)
            FontRegistry.bind_to_item(name, Font.REGULAR_SMALL)
