from functools import partial
from typing import Any, Callable, Optional, Tuple

import dearpygui.dearpygui as dpg

from sampletones_application.utils.gui.frame import FrameCallbackManager
from sampletones_application.utils.placement import centered_position


def viewport_center() -> Tuple[int, int]:
    """The middle of the space a window's position is measured in.

    A position given to DearPyGui stands in the viewport's client area, so the center it is
    measured against is read from the same space.
    """
    return dpg.get_viewport_client_width() // 2, dpg.get_viewport_client_height() // 2


def center_item(tag: str) -> None:
    if not dpg.does_item_exist(tag):
        return

    width, height = dpg.get_item_rect_size(tag)
    dpg.set_item_pos(tag, list(centered_position(viewport_center(), width, height)))


def center_when_settled(tag: str) -> None:
    """Holds a window centered over the frames it takes its size in, and lets go once it settles.

    A window that takes the size its content asks for reaches it over the frames it is drawn
    in: a form measures its fields on the second, and the keybindings list widens over a dozen
    more. Centering the window against every size it is read at keeps it centered the whole way
    there, and two readings that agree end the pass: a dialog can be dragged, and one that kept
    measuring would drag it back.
    """
    FrameCallbackManager.set_frame_callback(partial(_center_once_settled, tag, None))


def _center_once_settled(tag: str, previous: Optional[Tuple[int, int]]) -> None:
    """Centers the window where it now stands, and reads again while it is still growing."""
    if not dpg.does_item_exist(tag):
        return

    width, height = dpg.get_item_rect_size(tag)
    center_item(tag)
    if previous == (width, height):
        return

    FrameCallbackManager.set_frame_callback(partial(_center_once_settled, tag, (width, height)))


def table_wrapper(
    columns: int = 2,
    width: int = -1,
    height: int = -1,
    **kwargs: Any,
) -> Callable[[Callable[[Any], None]], Callable[[Any], None]]:
    def decorator(content: Callable[[Any], None]) -> Callable[[Any], None]:
        def wrapper(self: Any) -> None:
            with dpg.table(
                header_row=False,
                policy=dpg.mvTable_SizingStretchSame,
                resizable=False,
                width=width,
                height=height,
                **kwargs,
            ):
                for _ in range(columns):
                    dpg.add_table_column()

                with dpg.table_row():
                    content(self)

        return wrapper

    return decorator
