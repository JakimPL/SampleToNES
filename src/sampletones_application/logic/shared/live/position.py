from dataclasses import dataclass
from typing import Optional

from .strike import Strike


@dataclass(frozen=True)
class LivePosition:
    """Where the note a press struck stands, which the press's follower draws.

    Attributes:
        strike: The press whose note sounds.
        position: The sample of its voice the note has reached, counted from the strike at the rate its sound
            is synthesized under, which is the rate the voice is drawn at.
    """

    strike: Strike
    position: int


LiveReport = Optional[LivePosition]
