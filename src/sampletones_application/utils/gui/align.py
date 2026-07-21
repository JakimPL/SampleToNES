from typing import Any, Callable, Final, Tuple

import dearpygui.dearpygui as dpg

from sampletones_application.utils.gui.frame import FrameCallbackManager

_SETTLE_FRAMES: Final[int] = 2


def get_center(width: int, height: int) -> Tuple[int, int]:
    x = (dpg.get_viewport_width() - width) / 2
    y = (dpg.get_viewport_height() - height) / 2
    return round(x), round(y)


def center_item(tag: str) -> None:
    if not dpg.does_item_exist(tag):
        return

    width, height = dpg.get_item_rect_size(tag)
    x, y = get_center(width, height)
    dpg.set_item_pos(tag, [x, y])


def center_when_settled(tag: str) -> None:
    """Centres an autosizing window once its content has reached its final size.

    An autosize window measures its content across the first couple of frames, so a stretch
    table or wrapped text reaches its final width and height only on the second layout pass.
    Deferring the centre until then reads the settled size, so the window rests centred on its
    first appearance the same way a reopened one does from its remembered size.
    """
    FrameCallbackManager.set_frame_callback(
        lambda: center_item(tag),
        frame_count=_SETTLE_FRAMES,
    )


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
