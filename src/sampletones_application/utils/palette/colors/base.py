from abc import ABC, abstractmethod
from dataclasses import dataclass

from sampletones_shared.types.application import ColorRGBA


@dataclass(frozen=True)
class BaseColor(ABC):
    """A colour read at the moment it is drawn with.

    A colour keeps the form it was given rather than a value of its own, and :attr:`rgba`
    answers with what that form reads under the palette active right now, so the same object
    gives a new colour once another palette is activated. Consumers hold the colour and read
    :attr:`rgba` where they hand it to DearPyGui.

    Each form is a frozen dataclass carrying what it was written or composed from, which makes
    a colour hashable by that form and lets a theme cache key on the shade it holds. A form
    composed from other colours reads them through this same property, so a shade taken from a
    token follows a palette swap along with the colour it came from.
    """

    @property
    @abstractmethod
    def rgba(self) -> ColorRGBA:
        """The colour's value under the active palette."""
