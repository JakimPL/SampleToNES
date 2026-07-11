from contextlib import contextmanager
from typing import Iterator, Optional, Union

import dearpygui.dearpygui as dpg

from sampletones_application.ui.elements.fonts.font import Font
from sampletones_application.ui.elements.fonts.registry import FontRegistry


@contextmanager
def labeled_field(
    label: str,
    label_width: int,
    *,
    parent: Union[int, str] = 0,
    font: Optional[Font] = None,
) -> Iterator[None]:
    """Lay out a widget as ``label [ widget ]`` with the label in a fixed-width column.

    Opens a horizontal group holding the label text, pads it to ``label_width`` so the
    widget aligns with its neighbours, and yields inside the group for the caller to
    create the widget. The caller's widget omits its own ``label``.

    A ``font`` binds the label to that weight; leaving it unset keeps the default weight.
    """
    with dpg.group(horizontal=True, parent=parent):
        label_id = dpg.add_text(label)
        if font is not None:
            FontRegistry.bind_to_item(label_id, font)

        offset = label_width - int(dpg.get_text_size(label)[0])
        if offset > 0:
            dpg.add_spacer(width=offset)

        yield
