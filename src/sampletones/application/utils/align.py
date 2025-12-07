from typing import Any, Callable

import dearpygui.dearpygui as dpg


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
