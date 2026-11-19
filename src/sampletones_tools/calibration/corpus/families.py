from enum import StrEnum
from typing import Dict, Final


class Family(StrEnum):
    """A family of reference sounds, in the order a report and the page present them.

    The first four are sounds the channels play exactly, so the run knows every frame of them. The
    rest are sounds the channels approximate, the last of them kept for listening alone.
    """

    SINES = "sines"
    NOTES = "notes"
    CHORDS = "chords"
    SEQUENCES = "sequences"
    TONES = "tones"
    COMPOSITES = "composites"
    SAMPLES = "samples"


FAMILY_ORDER: Final[Dict[Family, int]] = {family: position for position, family in enumerate(Family)}
