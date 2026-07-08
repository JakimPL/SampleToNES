from dataclasses import dataclass
from typing import Callable, Sequence

import dearpygui.dearpygui as dpg

from sampletones_application.constants.general import TAG_GLOBAL_THEME_PANEL_GROUND
from sampletones_application.ui.themes.registry import ThemeRegistry

ColumnBuilder = Callable[[str], None]


@dataclass(frozen=True)
class ColumnSpec:
    """One column of a tab's layout, declared by the tab coordinator.

    ``build`` fills the column's child window, receiving the column ``tag`` as its
    parent. ``theme`` is the depth theme bound to the column background. A ``width``
    of ``0`` makes the column stretch to fill whatever the fixed columns leave; a
    positive ``width`` fixes it. A ``height`` of ``-1`` fills the tab vertically.
    """

    tag: str
    build: ColumnBuilder
    theme: str
    width: int = 0
    height: int = 0
    border: bool = True
    no_scrollbar: bool = False

    @property
    def stretches(self) -> bool:
        """Whether the column expands to absorb the space the fixed columns leave."""
        return self.width == 0


class TabColumns:
    """The shared scaffold every tab lays its panels out on.

    A tab is a recessed ground panel holding a row of columns separated by uniform
    gaps. Given the gap and an ordered column list, :meth:`build` constructs the
    ground wrapper, the gap-column table, and each column's child window, calls each
    column's builder to fill it, and binds the ground and per-column depth themes.
    This is the single owner of the tab column scaffold and of the columns' depth
    binding, so a coordinator declares its columns and delegates the structure here.
    """

    @classmethod
    def build(cls, *, panel_gap: int, columns: Sequence[ColumnSpec]) -> None:
        """Builds the ground wrapper and the column row from ``columns``, then binds their themes."""
        with dpg.child_window(
            width=-1,
            height=-panel_gap,
            border=False,
            no_scrollbar=True,
            no_scroll_with_mouse=True,
        ) as ground_wrapper:
            dpg.add_spacer(height=panel_gap)
            with dpg.table(
                header_row=False,
                resizable=False,
                policy=dpg.mvTable_SizingStretchProp,
            ):
                cls._declare_columns(panel_gap, columns)
                with dpg.table_row():
                    dpg.add_spacer()
                    for column in columns:
                        cls._build_column(column)
                        dpg.add_spacer()

        ThemeRegistry.get(TAG_GLOBAL_THEME_PANEL_GROUND).bind_to_item(ground_wrapper)
        for column in columns:
            ThemeRegistry.get(column.theme).bind_to_item(column.tag)

    @staticmethod
    def _declare_columns(panel_gap: int, columns: Sequence[ColumnSpec]) -> None:
        """Declares a fixed gap column before, between, and after the content columns."""
        dpg.add_table_column(width_fixed=True, init_width_or_weight=panel_gap)
        for column in columns:
            if column.stretches:
                dpg.add_table_column()
            else:
                dpg.add_table_column(width_fixed=True)
            dpg.add_table_column(width_fixed=True, init_width_or_weight=panel_gap)

    @staticmethod
    def _build_column(column: ColumnSpec) -> None:
        with dpg.child_window(
            tag=column.tag,
            width=column.width,
            height=column.height,
            border=column.border,
            no_scrollbar=column.no_scrollbar,
            no_scroll_with_mouse=True,
        ):
            column.build(column.tag)
