from typing import Dict, Optional, Tuple

import dearpygui.dearpygui as dpg

from sampletones.typehints import SerializedData

from ...constants import (
    COL_TABLE_LABEL,
    COL_TABLE_VALUE,
    DIM_TABLE_LABEL_WIDTH,
    TAG_FONT_BOLD,
)
from ...themes.table import TableTheme
from ...themes.theme import Theme
from .cell import TableCell


class GUITable:
    REGISTRY: Dict[str, "GUITable"] = {}

    def __init__(
        self,
        tag: str,
        rows: Tuple[TableCell, ...],
        parent: Optional[str] = None,
        before: Optional[str] = None,
        label_column_width: int = DIM_TABLE_LABEL_WIDTH,
        header_row: bool = False,
        borders_inner_horizontal: bool = True,
        borders_outer_horizontal: bool = True,
        borders_inner_vertical: bool = True,
        borders_outer_vertical: bool = True,
        row_background: bool = True,
        resizable: bool = False,
        label_color: Tuple[int, int, int, int] = COL_TABLE_LABEL,
        value_color: Tuple[int, int, int, int] = COL_TABLE_VALUE,
        bold_labels: bool = True,
        theme: Theme = TableTheme(),
    ) -> None:
        self._tag = tag
        self._rows = rows
        self._label_column_width = label_column_width
        self._label_color = label_color
        self._value_color = value_color
        self._bold_labels = bold_labels
        self._theme = theme

        table_kwargs: SerializedData = {
            "tag": tag,
            "header_row": header_row,
            "borders_innerH": borders_inner_horizontal,
            "borders_outerH": borders_outer_horizontal,
            "borders_innerV": borders_inner_vertical,
            "borders_outerV": borders_outer_vertical,
            "row_background": row_background,
            "resizable": resizable,
            "policy": dpg.mvTable_SizingFixedFit,
        }

        if parent is not None:
            table_kwargs["parent"] = parent

        if before is not None:
            table_kwargs["before"] = before

        with dpg.table(**table_kwargs):
            self._theme.bind_to_item(tag)
            dpg.add_table_column(width_fixed=True, init_width_or_weight=label_column_width)
            dpg.add_table_column(width_stretch=True)

            for row in rows:
                self._add_row(row)

        GUITable.REGISTRY[tag] = self

    def _add_row(self, cell: TableCell) -> None:
        with dpg.table_row():
            label_text = dpg.add_text(cell.label)
            if self._bold_labels:
                dpg.bind_item_font(label_text, TAG_FONT_BOLD)
            dpg.configure_item(label_text, color=self._label_color)

            value_text = dpg.add_text(cell.value)
            dpg.configure_item(value_text, color=self._value_color)

    @classmethod
    def delete(cls, tag: str) -> None:
        if tag in cls.REGISTRY:
            if dpg.does_item_exist(tag):
                dpg.delete_item(tag)
            del cls.REGISTRY[tag]

    def delete_item(self) -> None:
        if dpg.does_item_exist(self._tag):
            dpg.delete_item(self._tag)
        if self._tag in GUITable.REGISTRY:
            del GUITable.REGISTRY[self._tag]

    def show(self) -> None:
        dpg.configure_item(self._tag, show=True)

    def hide(self) -> None:
        dpg.configure_item(self._tag, show=False)

    def set_visible(self, visible: bool) -> None:
        dpg.configure_item(self._tag, show=visible)

    def is_visible(self) -> bool:
        visible: Optional[bool] = dpg.is_item_visible(self._tag)
        return visible if visible is not None else False

    def configure_item(self, show: Optional[bool] = None) -> None:
        kwargs: Dict[str, object] = {}
        if show is not None:
            kwargs["show"] = show
        if kwargs:
            dpg.configure_item(self._tag, **kwargs)

    @property
    def tag(self) -> str:
        return self._tag

    @property
    def rows(self) -> Tuple[TableCell, ...]:
        return self._rows
