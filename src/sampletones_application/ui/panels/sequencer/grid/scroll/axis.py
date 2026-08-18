from typing import Protocol

import dearpygui.dearpygui as dpg


class ScrollAxis(Protocol):
    """The axis one table scrolls along, and the pointer coordinate that runs past its edges."""

    def pointer(self) -> float: ...

    def scroll(self) -> float: ...

    def scroll_max(self) -> float: ...

    def set_scroll(self, offset: float) -> None: ...


class VerticalScroll:
    """A table whose rows run down the screen, so the pointer's height names the cell it stands on."""

    def __init__(self, *, table: str) -> None:
        self._table = table

    def pointer(self) -> float:
        _, top = dpg.get_mouse_pos(local=False)
        return float(top)

    def scroll(self) -> float:
        return float(dpg.get_y_scroll(self._table))

    def scroll_max(self) -> float:
        return float(dpg.get_y_scroll_max(self._table))

    def set_scroll(self, offset: float) -> None:
        dpg.set_y_scroll(self._table, offset)


class HorizontalScroll:
    """A table whose columns run across the screen, so the pointer's width names the cell it stands on."""

    def __init__(self, *, table: str) -> None:
        self._table = table

    def pointer(self) -> float:
        left, _ = dpg.get_mouse_pos(local=False)
        return float(left)

    def scroll(self) -> float:
        return float(dpg.get_x_scroll(self._table))

    def scroll_max(self) -> float:
        return float(dpg.get_x_scroll_max(self._table))

    def set_scroll(self, offset: float) -> None:
        dpg.set_x_scroll(self._table, offset)
