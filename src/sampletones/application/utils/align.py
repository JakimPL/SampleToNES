from typing import Any, Callable

import dearpygui.dearpygui as dpg


def table_wrapper(
    rows: int = 1,
    columns: int = 2,
    width: int = -1,
    height: int = -1,
) -> Callable[[Callable[[Any], None]], Callable[[Any], None]]:
    def decorator(content: Callable[[Any], None]) -> Callable[[Any], None]:
        def wrapper(self: Any) -> None:
            with dpg.table(
                header_row=False,
                policy=dpg.mvTable_SizingStretchProp,
                resizable=False,
                width=width,
                height=height,
            ):
                for _ in range(rows * columns):
                    dpg.add_table_column()

                with dpg.table_row():
                    content(self)

        return wrapper

    return decorator
