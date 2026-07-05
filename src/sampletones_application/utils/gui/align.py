from typing import Any, Callable

import dearpygui.dearpygui as dpg


def get_center(width: int, height: int) -> tuple[int, int]:
    x = (dpg.get_viewport_width() - width) / 2
    y = (dpg.get_viewport_height() - height) / 2
    return round(x), round(y)


def center_item(tag: str, width: int, height: int) -> None:
    if not dpg.does_item_exist(tag):
        return

    width, height = dpg.get_item_rect_size(tag)
    x, y = get_center(width, height)
    dpg.set_item_pos(tag, [x, y])


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
