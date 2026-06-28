from typing import List, Tuple

import dearpygui.dearpygui as dpg

from sampletones_application.constants.general import (
    TAG_GLOBAL_STATUS_BAR,
    TAG_GLOBAL_THEME_TOOLTIP,
    TAG_GLOBAL_THEME_TOOLTIP_TABLE,
)
from sampletones_application.ui.elements.fonts.font import Font
from sampletones_application.ui.elements.fonts.registry import FontRegistry
from sampletones_application.ui.themes.registry import ThemeRegistry
from sampletones_shared.types.application import Sender


def show_tooltip(parent: str, message: str) -> Sender:
    with dpg.tooltip(parent, hide_on_activity=True) as tooltip:
        ThemeRegistry.get(TAG_GLOBAL_THEME_TOOLTIP).bind_to_item(tooltip)
        tooltip_text: Sender = dpg.add_text(message)
        FontRegistry.bind_to_item(tooltip_text, Font.REGULAR_SMALL)

    return tooltip_text


def attach_disabled_tooltip(parent: str, message: str, *, tag: str) -> None:
    """Attaches an explanatory tooltip to ``parent`` — an enabled group wrapping a control that can be
    disabled — and hides it by default. Toggle ``tag``'s ``show`` to reveal the explanation while the
    control is unavailable. The wrapper group is the hover target because DearPyGui surfaces a tooltip
    for an enabled item, so the explanation reaches the user even when the inner control is disabled."""
    with dpg.tooltip(parent, tag=tag, show=False, hide_on_activity=True) as tooltip:
        ThemeRegistry.get(TAG_GLOBAL_THEME_TOOLTIP).bind_to_item(tooltip)
        tooltip_text = dpg.add_text(message)
        FontRegistry.bind_to_item(tooltip_text, Font.REGULAR_SMALL)


def show_detail_tooltip(parent: str, items: List[Tuple[str, str]]) -> None:
    """Attaches a hover tooltip rendering ``label``/``value`` pairs in two aligned columns.

    ``mvTable_SizingFixedFit`` sizes each column to its own content, so the label column tracks its
    own text width independently of the value column. A compact theme tightens the row padding.
    """
    with dpg.tooltip(parent, hide_on_activity=True) as tooltip:
        ThemeRegistry.get(TAG_GLOBAL_THEME_TOOLTIP).bind_to_item(tooltip)
        with dpg.table(
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
