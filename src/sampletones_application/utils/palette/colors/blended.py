from dataclasses import dataclass

from sampletones_application.utils.palette.colors.base import BaseColor
from sampletones_shared.types.application import ColorRGBA
from sampletones_shared.utils.color import blend


@dataclass(frozen=True)
class BlendedColor(BaseColor):
    """A colour carried as a point on the gradient between two others, channel by channel."""

    start: BaseColor
    end: BaseColor
    fraction: float

    @property
    def rgba(self) -> ColorRGBA:
        """Both ends' values under the active palette, mixed at the carried fraction."""
        return blend(self.start.rgba, self.end.rgba, self.fraction)
