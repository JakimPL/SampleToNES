from typing import NamedTuple


class PhraseMatch(NamedTuple):
    """A phrase the plane plays from a tick, and the terms it plays it on.

    Attributes:
        phrase_id: Position the phrase takes in the table.
        ticks: The ticks the plane plays of it, its final value held past its end.
        transpose: The shift every byte of it is played at.
    """

    phrase_id: int
    ticks: int
    transpose: int
