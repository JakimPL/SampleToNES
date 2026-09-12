from dataclasses import dataclass
from typing import AbstractSet, Final, Optional, Sequence

import dearpygui.dearpygui as dpg

from sampletones_application.tags.compose import compose_tag
from sampletones_application.tags.general import (
    SUF_TABLE_COLUMN,
    SUF_TABLE_GAP,
    TAG_GLOBAL_THEME_PANEL_GROUND,
)
from sampletones_application.ui.themes.registry import ThemeRegistry
from sampletones_application.utils.gui.dpg import dpg_configure_item
from sampletones_shared.types.application import Sender
from sampletones_shared.types.callback import StringCallback

_STRETCH_WEIGHT: Final[float] = 1.0
_PUT_AWAY: Final[float] = 0.0


@dataclass(frozen=True)
class ColumnSpec:
    """One column of a tab's layout, declared by the tab coordinator.

    ``build`` fills the column, receiving the column ``tag`` as its parent. ``theme``,
    when given, is the depth theme bound to the column background; a card-hosting column
    leaves it unset so the card owns its own surface. A ``width`` of ``0`` makes the
    column stretch to fill whatever the fixed columns leave; a positive ``width`` fixes
    it. A ``height`` of ``-1`` fills the tab vertically.
    """

    tag: str
    build: StringCallback
    theme: Optional[str] = None
    width: int = 0
    height: int = 0
    border: bool = True
    no_scrollbar: bool = False

    @property
    def stretches(self) -> bool:
        """Whether the column expands to absorb the space the fixed columns leave."""
        return self.width == 0

    @property
    def declared_size(self) -> float:
        """The share a stretching column takes of what is left, or the width a fixed one holds."""
        return _STRETCH_WEIGHT if self.stretches else float(self.width)


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
    def build(
        cls,
        *,
        panel_gap: int,
        columns: Sequence[ColumnSpec],
    ) -> int:
        """Builds the ground wrapper and the column row from ``columns``, then binds their themes.

        Returns the number of fixed-width side columns — the ones that hold their width while the
        center stretches — which the responsive width sizing shares the viewport's surplus among.
        """
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
        cls._bind_column_themes(columns)
        return sum(1 for column in columns if not column.stretches)

    @classmethod
    def row(
        cls,
        *,
        panel_gap: int,
        columns: Sequence[ColumnSpec],
        height: int = 0,
        tag: Sender = 0,
    ) -> None:
        """Lays a gap-separated row of columns flush inside the container already on the stack.

        Where :meth:`build` frames a whole tab, ``row`` composes a side-by-side group inside a
        column a coordinator already owns: it drops the ground wrapper and the outer gaps, so the
        columns sit flush to the container edges with a single gap between each neighbor. Each
        column's builder fills its cell directly, letting the hosted cards own their own surface.
        A ``height`` of ``0`` sizes the row to its content. A ``tag`` names the row table so a
        coordinator can resize it when its hosted cards collapse.
        """
        with dpg.table(
            header_row=False,
            resizable=False,
            policy=dpg.mvTable_SizingStretchProp,
            width=-1,
            height=height,
            tag=tag,
        ):
            cls._declare_row_columns(panel_gap, columns)
            with dpg.table_row():
                for index, column in enumerate(columns):
                    if index > 0:
                        dpg.add_spacer()

                    with dpg.table_cell(tag=column.tag):
                        column.build(column.tag)

        cls._bind_column_themes(columns)

    @classmethod
    def stand_columns(
        cls,
        columns: Sequence[ColumnSpec],
        standing: AbstractSet[str],
        panel_gap: int,
    ) -> None:
        """Divides a row built by :meth:`row` among the columns in ``standing``.

        A card the reader puts away leaves its column with nothing to hold, so the column drops to
        no width and the ones still standing divide the whole row between them. A gap holds its
        width where a column stands on each side of it, so what is left sits flush to the row's
        edges and keeps one gap between neighbors. A column comes back at the size it was declared
        with.
        """
        preceded = False
        for index, column in enumerate(columns):
            stands = column.tag in standing
            dpg_configure_item(
                compose_tag(column.tag, SUF_TABLE_COLUMN),
                init_width_or_weight=column.declared_size if stands else _PUT_AWAY,
            )
            if index > 0:
                dpg_configure_item(
                    compose_tag(column.tag, SUF_TABLE_GAP),
                    init_width_or_weight=panel_gap if stands and preceded else _PUT_AWAY,
                )

            preceded = preceded or stands

    @staticmethod
    def _bind_column_themes(columns: Sequence[ColumnSpec]) -> None:
        """Binds each column's declared depth theme, leaving card-hosting columns to their cards."""
        for column in columns:
            if column.theme is not None:
                ThemeRegistry.get(column.theme).bind_to_item(column.tag)

    @staticmethod
    def _declare_columns(panel_gap: int, columns: Sequence[ColumnSpec]) -> None:
        """Declares a fixed gap column before, between, and after the content columns."""
        dpg.add_table_column(
            width_fixed=True,
            init_width_or_weight=panel_gap,
        )
        for column in columns:
            if column.stretches:
                dpg.add_table_column()

            else:
                dpg.add_table_column(width_fixed=True)

            dpg.add_table_column(
                width_fixed=True,
                init_width_or_weight=panel_gap,
            )

    @staticmethod
    def _declare_row_columns(
        panel_gap: int,
        columns: Sequence[ColumnSpec],
    ) -> None:
        """Declares each content column at the size it states, with a fixed gap between neighbors.

        A stretching column takes an explicit share rather than one read back from the card inside
        it, so the row keeps the proportions it was declared with whatever its cards draw. Each
        column and each gap is named after the cell it serves, which is how :meth:`stand_columns`
        reaches them once the row is standing.
        """
        for index, column in enumerate(columns):
            if index > 0:
                dpg.add_table_column(
                    width_fixed=True,
                    init_width_or_weight=panel_gap,
                    tag=compose_tag(column.tag, SUF_TABLE_GAP),
                )

            dpg.add_table_column(
                width_stretch=column.stretches,
                width_fixed=not column.stretches,
                init_width_or_weight=column.declared_size,
                tag=compose_tag(column.tag, SUF_TABLE_COLUMN),
            )

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
