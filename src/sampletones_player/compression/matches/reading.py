from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class PhraseReading:
    """What one phrase plays against one plane, read once for a whole encoding.

    The ticks answer a parse asking what a token from a position would cover. The reach answers
    the search asking whether a plane needs reading again at all: a phrase the plane never plays
    leaves that plane's tokens exactly as they were.

    Attributes:
        ticks: The ticks the phrase plays for from each tick of the plane.
        shifted: Whether the plane plays the phrase anywhere, at whatever shift it asks for.
        unshifted: Whether the plane plays the phrase anywhere at the pitch it was stored at.
    """

    ticks: Sequence[int]
    shifted: bool
    unshifted: bool

    def reaches(self, *, transposition: bool) -> bool:
        """Whether the plane plays the phrase under the layers the encoding is built from.

        Args:
            transposition: Whether a phrase may play at a shift.

        Returns:
            bool: Whether the phrase reaches the plane at all.
        """
        return self.shifted if transposition else self.unshifted
