from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from sampletones_shared.types.application import ColorRGBA
from sampletones_shared.utils.color import blend, to_grayscale, with_alpha_fraction


@dataclass(frozen=True)
class BaseColor(ABC):
    """A colour read at the moment it is drawn with.

    A colour keeps the form it was given rather than a value of its own, and :attr:`rgba`
    answers with what that form reads under the palette active right now, so the same
    object gives a new colour once another palette is activated. Consumers hold the colour
    and read :attr:`rgba` where they hand it to DearPyGui.
    """

    @property
    @abstractmethod
    def rgba(self) -> ColorRGBA:
        """The colour's value under the active palette."""

    def faded(self, fraction: float) -> BaseColor:
        """This colour at ``fraction`` of full opacity, keeping its red, green and blue."""

        @dataclass(frozen=True)
        class FadedColor(BaseColor):

            base: BaseColor
            fraction: float

            @property
            def rgba(self) -> ColorRGBA:
                return with_alpha_fraction(self.base.rgba, self.fraction)

        return FadedColor(self, fraction)

    def grayscale(self) -> BaseColor:
        """This colour desaturated to the gray of the same luminance, keeping its alpha."""

        @dataclass(frozen=True)
        class GrayscaleColor(BaseColor):

            base: BaseColor

            @property
            def rgba(self) -> ColorRGBA:
                return to_grayscale(self.base.rgba)

        return GrayscaleColor(self)

    def blended(self, other: BaseColor, fraction: float) -> BaseColor:
        """The colour ``fraction`` of the way from this one to ``other``, channel by channel."""

        @dataclass(frozen=True)
        class BlendedColor(BaseColor):
            start: BaseColor
            end: BaseColor
            fraction: float

            @property
            def rgba(self) -> ColorRGBA:
                return blend(self.start.rgba, self.end.rgba, self.fraction)

        return BlendedColor(self, other, fraction)
