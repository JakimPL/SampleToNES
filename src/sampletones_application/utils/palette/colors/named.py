from dataclasses import dataclass

from sampletones_application.utils.palette.colors.base import BaseColor
from sampletones_application.utils.palette.reference import PaletteReference
from sampletones_application.utils.palette.source import PaletteSource
from sampletones_shared.types.application import ColorRGBA


@dataclass(frozen=True)
class NamedColor(BaseColor):
    """A colour written as a palette reference, together with the source that answers it."""

    reference: PaletteReference
    source: PaletteSource

    @property
    def rgba(self) -> ColorRGBA:
        """The value the active palette gives the referenced token.

        Raises:
            KeyError: when that palette holds no token of the referenced name.
        """
        return self.source.palette.resolve(self.reference)
