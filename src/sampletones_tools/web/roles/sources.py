from dataclasses import dataclass
from enum import Enum
from typing import Callable, Protocol

from sampletones_application.layout.general import GeneralLayout
from sampletones_application.utils.palette.colors.base import BaseColor
from sampletones_application.utils.theme.catalog import ThemeEntryAddress
from sampletones_shared.types.application import ColorRGBA
from sampletones_tools.web.design import ApplicationDesign


class Axis(Enum):
    X = "x"
    Y = "y"


class ColorRole(Protocol):
    """Where a page's color comes from in the application's configuration."""

    def resolve(self, design: ApplicationDesign) -> ColorRGBA: ...


class DimensionRole(Protocol):
    """Where a page's size comes from in the application's configuration, in application pixels."""

    def resolve(self, design: ApplicationDesign) -> float: ...


@dataclass(frozen=True)
class ThemeColorRole:
    """The color a theme gives one entry, the way the widget bound to that theme draws it."""

    theme: str
    address: ThemeEntryAddress

    def resolve(self, design: ApplicationDesign) -> ColorRGBA:
        return design.themes.color(self.theme, self.address).rgba


@dataclass(frozen=True)
class LayoutColorRole:
    """A color the general layout states, such as a channel's or a link's."""

    read: Callable[[GeneralLayout], BaseColor]

    def resolve(self, design: ApplicationDesign) -> ColorRGBA:
        return self.read(design.general).rgba


@dataclass(frozen=True)
class ThemeDimensionRole:
    """One component of a style a theme states, such as a rounding or a padding."""

    theme: str
    address: ThemeEntryAddress
    axis: Axis

    def resolve(self, design: ApplicationDesign) -> float:
        x, y = design.themes.style(self.theme, self.address)
        return x if self.axis is Axis.X or y < 0 else y


@dataclass(frozen=True)
class LayoutDimensionRole:
    """A size the general layout states, such as the card header's height."""

    read: Callable[[GeneralLayout], float]

    def resolve(self, design: ApplicationDesign) -> float:
        return self.read(design.general)
