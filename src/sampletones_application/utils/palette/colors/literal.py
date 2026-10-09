from dataclasses import dataclass

from sampletones_application.utils.palette.colors.base import BaseColor
from sampletones_shared.types.application import ColorRGBA


@dataclass(frozen=True)
class LiteralColor(BaseColor):
    """A color written as a ``#rrggbb`` value, standing on its own."""

    value: ColorRGBA

    @property
    def rgba(self) -> ColorRGBA:
        """The value the color was written with."""
        return self.value
