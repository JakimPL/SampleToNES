from contextlib import contextmanager
from typing import Final, Iterator

import dearpygui.dearpygui as dpg

EQUAL_SHARE: Final[float] = 1.0


@contextmanager
def centered() -> Iterator[None]:
    """Stand what the block builds in the middle of the width it is offered.

    The content sits in a column fitted to it, flanked by two columns sharing the rest of the width
    equally. The fitted column follows the content from frame to frame, so a label that grows or
    shrinks while it stands stays centered.
    """
    with dpg.table(header_row=False):
        dpg.add_table_column(width_stretch=True, init_width_or_weight=EQUAL_SHARE)
        dpg.add_table_column(width_fixed=True)
        dpg.add_table_column(width_stretch=True, init_width_or_weight=EQUAL_SHARE)
        with dpg.table_row():
            dpg.add_spacer()
            with dpg.group():
                yield

            dpg.add_spacer()
