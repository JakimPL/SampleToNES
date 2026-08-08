from dataclasses import dataclass

from sampletones_application.utils.palette.colors.base import BaseColor
from sampletones_shared.types.application import ColorRGBA
from sampletones_shared.utils.color import to_grayscale


@dataclass(frozen=True)
class GrayscaleColor(BaseColor):
    """A colour carried as the gray of the same luminance, keeping its alpha."""

    color: BaseColor

    @property
    def rgba(self) -> ColorRGBA:
        """The carried colour's value under the active palette, desaturated."""
        return to_grayscale(self.color.rgba)
