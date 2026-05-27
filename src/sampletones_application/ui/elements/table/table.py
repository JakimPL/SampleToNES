from __future__ import annotations

from typing import Dict, List, Optional, Tuple

import dearpygui.dearpygui as dpg

from sampletones_application.constants.general import COL_TABLE_LABEL, COL_TABLE_VALUE, DIM_TABLE_WIDTH_LABEL
from sampletones_application.logic.instruction.cell import TableCell
from sampletones_application.ui.elements.fonts.font import Font
from sampletones_application.ui.elements.fonts.registry import FontRegistry
from sampletones_application.ui.themes.tables.table import TableTheme
from sampletones_application.ui.themes.theme import Theme
from sampletones_application.utils.dpg import dpg_delete_children
from sampletones_shared.types.application import Color, Sender
from sampletones_shared.types.data import SerializedData


class GUITable:
    _REGISTRY: Dict[str, GUITable] = {}

    def __init__(
        self,
        tag: str,
        rows: Tuple[TableCell, ...],
        parent: Optional[str] = None,
        before: Optional[str] = None,
        label_column_width: int = DIM_TABLE_WIDTH_LABEL,
        header_row: bool = False,
        borders_inner_horizontal: bool = True,
        borders_outer_horizontal: bool = True,
        borders_inner_vertical: bool = True,
        borders_outer_vertical: bool = True,
        row_background: bool = True,
        resizable: bool = False,
        label_color: Color = COL_TABLE_LABEL,
        value_color: Color = COL_TABLE_VALUE,
        bold_labels: bool = True,
        theme: Theme = TableTheme(),
    ) -> None:
        self._tag = tag

        self._rows = rows
        self._labels: List[Sender] = []
        self._values: List[Sender] = []

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

        table_kwargs["show"] = bool(rows)
        dpg.add_table(**table_kwargs)
        self.update_rows(rows)

        GUITable._REGISTRY[tag] = self

    def _reset(self) -> None:
        self._rows = ()
        self._labels = []
        self._values = []

        dpg_delete_children(self._tag)
        self._theme.bind_to_item(self._tag)
        dpg.add_table_column(
            width_fixed=True,
            init_width_or_weight=self._label_column_width,
            parent=self._tag,
        )
        dpg.add_table_column(width_stretch=True, parent=self._tag)

    def update_rows(self, rows: Tuple[TableCell, ...] = (), clear: bool = True) -> None:
        if clear:
            self._reset()
            self._add_rows(rows)
        else:
            self._update_values(rows)

        self.set_visibility(bool(rows))

    def _add_rows(self, rows: Tuple[TableCell, ...]) -> None:
        for row in rows:
            self._add_row(row)

    def _update_values(self, rows: Tuple[TableCell, ...]) -> None:
        for i, row in enumerate(rows):
            value = row.value
            dpg.set_value(self._values[i], value)

    def clear(self) -> None:
        self._reset()
        self._rows = ()
        self.update_rows()

    def _add_row(self, cell: TableCell) -> None:
        with dpg.table_row(parent=self._tag):
            label_text = dpg.add_text(cell.label)
            label_font = Font.BOLD_SMALL if self._bold_labels else Font.REGULAR_SMALL
            FontRegistry.bind_to_item(label_text, label_font)
            dpg.configure_item(label_text, color=self._label_color)
            self._labels.append(label_text)

            value_text = dpg.add_text(cell.value)
            FontRegistry.bind_to_item(value_text, Font.REGULAR_SMALL)
            dpg.configure_item(value_text, color=self._value_color)
            self._values.append(value_text)

    @classmethod
    def delete(cls, tag: str) -> None:
        if tag in cls._REGISTRY:
            if dpg.does_item_exist(tag):
                dpg.delete_item(tag)
            del cls._REGISTRY[tag]

    def delete_item(self) -> None:
        if dpg.does_item_exist(self._tag):
            dpg.delete_item(self._tag)
        if self._tag in GUITable._REGISTRY:
            del GUITable._REGISTRY[self._tag]

    def show(self) -> None:
        dpg.configure_item(self._tag, show=True)

    def hide(self) -> None:
        dpg.configure_item(self._tag, show=False)

    def set_visibility(self, visible: bool) -> None:
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
