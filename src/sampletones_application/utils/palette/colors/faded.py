from dataclasses import dataclass

from sampletones_application.utils.palette.colors.base import BaseColor
from sampletones_shared.types.application import ColorRGBA
from sampletones_shared.utils.color import with_alpha_fraction


@dataclass(frozen=True)
class FadedColor(BaseColor):
    """A colour carried at a fraction of full opacity, keeping its red, green and blue."""

    color: BaseColor
    fraction: float

    @property
    def rgba(self) -> ColorRGBA:
        """The carried colour's value under the active palette, at the carried opacity."""
        return with_alpha_fraction(self.color.rgba, self.fraction)
