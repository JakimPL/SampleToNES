from enum import StrEnum
from typing import Iterable, Self


class Agreement(StrEnum):
    """How a group of recordings stands on one choice: all of them make it, some do, or none does.

    A row standing for several recordings shows this reading, and one gesture settles the whole
    group from it.
    """

    NONE = "none"
    SOME = "some"
    ALL = "all"

    @classmethod
    def over(cls, holdings: Iterable[bool]) -> Self:
        """The reading a group of recordings gives, each stating whether it makes the choice.

        A group holding nothing reads as ``NONE``, which is what an empty folder shows.
        """
        readings = tuple(holdings)
        if readings and all(readings):
            return cls.ALL

        return cls.SOME if any(readings) else cls.NONE

    @property
    def settles_to(self) -> bool:
        """What one gesture makes of this reading: every recording holds the choice.

        A group already agreeing on it lets it go instead, so a reader reaches both answers from
        wherever the group stands.
        """
        return self is not Agreement.ALL
