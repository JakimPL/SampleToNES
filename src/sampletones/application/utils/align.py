from typing import Any, Callable

import dearpygui.dearpygui as dpg


def table_wrapper(content: Callable[[Any], None]) -> Callable[[Any], None]:
    def wrapper(self: Any) -> None:
        with dpg.table(
            header_row=False,
            policy=dpg.mvTable_SizingStretchProp,
            resizable=False,
            width=-1,
            height=-1,
        ):
            dpg.add_table_column()
            dpg.add_table_column()

            with dpg.table_row():
                content(self)

    return wrapper
