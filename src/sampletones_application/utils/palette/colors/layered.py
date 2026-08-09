from dataclasses import dataclass

from sampletones_application.utils.palette.colors.base import BaseColor
from sampletones_shared.types.application import ColorRGBA
from sampletones_shared.utils.color import composite


@dataclass(frozen=True)
class LayeredColor(BaseColor):
    """A colour carried as one wash drawn over another, kept as the two it was composed from.

    A surface that offers a single tint takes both washes through this form: the pair keeps
    following the palette, and the value handed over is the shade the two make together.
    """

    base: BaseColor
    overlay: BaseColor

    @property
    def rgba(self) -> ColorRGBA:
        """Both washes' values under the active palette, the overlay covering the base."""
        return composite(self.base.rgba, self.overlay.rgba)
