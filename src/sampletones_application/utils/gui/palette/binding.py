from dataclasses import dataclass
from typing import Final, Tuple, Union

import dearpygui.dearpygui as dpg

from sampletones_application.utils.palette.colors.base import BaseColor
from sampletones_shared.types.application import Sender

ArgumentKey = Tuple[Sender, str]

COLOR_ARGUMENT: Final[str] = "color"


@dataclass(frozen=True)
class ArgumentBinding:
    """A colour DearPyGui copied into one of an item's arguments."""

    item: Sender
    color: BaseColor
    argument: str

    def push(self) -> None:
        dpg.configure_item(self.item, **{self.argument: self.color.rgba})


@dataclass(frozen=True)
class ThemeColorBinding:
    """A colour DearPyGui copied into a theme colour item."""

    item: Sender
    color: BaseColor

    def push(self) -> None:
        dpg.set_value(self.item, self.color.rgba)


PaletteBinding = Union[ArgumentBinding, ThemeColorBinding]
