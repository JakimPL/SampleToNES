from typing import List, Optional, Tuple

import dearpygui.dearpygui as dpg

from sampletones_application.tags.general import (
    TAG_GLOBAL_STATUS_BAR,
    TAG_GLOBAL_THEME_TOOLTIP,
    TAG_GLOBAL_THEME_TOOLTIP_TABLE,
)
from sampletones_application.ui.elements.fonts.font import Font
from sampletones_application.ui.elements.fonts.registry import FontRegistry
from sampletones_application.ui.themes.registry import ThemeRegistry
from sampletones_shared.types.application import Sender
from sampletones_shared.types.data import SerializedData


def show_tooltip(
    parent: str,
    message: str,
    *,
    tag: Optional[str] = None,
) -> Sender:
    tooltip_kwargs: SerializedData = {"hide_on_activity": True}
    if tag is not None:
        tooltip_kwargs["tag"] = tag

    with dpg.tooltip(parent, **tooltip_kwargs) as tooltip:
        ThemeRegistry.get(TAG_GLOBAL_THEME_TOOLTIP).bind_to_item(tooltip)
        tooltip_text: Sender = dpg.add_text(message)
        FontRegistry.bind_to_item(tooltip_text, Font.REGULAR_SMALL)

    return tooltip_text


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


def populate_detail_tooltip(tag: str, items: List[Tuple[str, str]]) -> None:
    """Replaces the tooltip's content with ``label``/``value`` pairs in two aligned columns.

    ``mvTable_SizingFixedFit`` sizes each column to its own content, so the label column tracks its
    own text width independently of the value column. A compact theme tightens the row padding.
    """
    dpg.delete_item(tag, children_only=True)
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
                FontRegistry.bind_to_item(value_text, Font.REGULAR_SMALL)


def show_status(message: str) -> None:
    dpg.set_value(TAG_GLOBAL_STATUS_BAR, message)
