from dataclasses import dataclass
from pathlib import Path

import dearpygui.dearpygui as dpg

from sampletones_application.layout.general.colors.path import PathColors
from sampletones_application.ui.elements.button import GUIButton
from sampletones_application.ui.elements.field import labeled_field
from sampletones_application.ui.elements.fonts.font import Font
from sampletones_application.ui.elements.path import GUIDestinationPathText
from sampletones_application.ui.elements.status import GUIStatusBar
from sampletones_shared.types.callback import VoidCallback


@dataclass(frozen=True)
class DestinationRow:
    """What a dialog's destination row is labeled and tagged with.

    Attributes:
        on_browse: What the browse button asks for.
        label: The words the row is labeled with.
        browse_label: The words on the button that asks for another file.
        group_tag: The tag of the horizontal group the button and the path stand in.
        button_tag: The browse button's tag.
        path_tag: The tag of the text naming the file.
    """

    on_browse: VoidCallback
    label: str
    browse_label: str
    group_tag: str
    button_tag: str
    path_tag: str


@dataclass(frozen=True)
class DestinationStyle:
    """How a dialog draws its destination row: the label column, the path's colors and the status
    line a hovered path speaks on."""

    label_width: int
    path_colors: PathColors
    status_message: str
    status_bar: GUIStatusBar


def destination_row(row: DestinationRow, *, path: Path, style: DestinationStyle) -> GUIDestinationPathText:
    """Lays out the file a dialog writes, with the browse button leading the path it stands at.

    The button leads the row so it holds its place whatever the path reads, and the path follows
    it as the answer to what the button asks.

    Returns:
        GUIDestinationPathText: The text naming the file, which the dialog updates as it changes.
    """
    with labeled_field(row.label, style.label_width):
        dpg.add_group(horizontal=True, tag=row.group_tag)

    GUIButton(tag=row.button_tag, label=row.browse_label, parent=row.group_tag, callback=row.on_browse)
    return GUIDestinationPathText(
        tag=row.path_tag,
        path=path,
        parent=row.group_tag,
        color=style.path_colors.default,
        hover_color=style.path_colors.hover,
        status_message=style.status_message,
        font=Font.REGULAR_SMALL,
        status_bar=style.status_bar,
    )
