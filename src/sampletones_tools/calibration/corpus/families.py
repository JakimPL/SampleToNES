from enum import StrEnum
from typing import Dict, Final, List, Tuple


class Family(StrEnum):
    """A family of reference sounds, in the order a report and the page present them.

    ``NOTES``, ``CHORDS`` and ``SEQUENCES`` are written as NES frames, so the channels play them
    exactly and the run knows every frame of them. ``SINES`` and ``TONES`` are synthesized, the
    channels approximate them, and the run knows the pitch of those holding one. ``COMPOSITES`` hold
    several sounds together, and ``SAMPLES`` are recordings kept for listening alone.
    """

    SINES = "sines"
    NOTES = "notes"
    CHORDS = "chords"
    SEQUENCES = "sequences"
    TONES = "tones"
    COMPOSITES = "composites"
    SAMPLES = "samples"


FAMILY_ORDER: Final[Dict[Family, int]] = {family: position for position, family in enumerate(Family)}

Catalog = List[Tuple[Family, str]]
