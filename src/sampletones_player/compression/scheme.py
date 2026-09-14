from enum import StrEnum
from typing import Tuple

from sampletones_player.compression.options import EVERY_LAYER, CodecOptions


class CompressionScheme(StrEnum):
    """How hard a song is compressed, stated as the layers of the codec it is written with.

    Each scheme keeps the layers of the one before it and adds its own, so the choice runs from a
    song spelled out value by value to the smallest encoding the codec reaches, and the time an
    export spends grows along the way. Every scheme writes a song the driver plays.
    """

    NONE = "none"
    RUNS = "runs"
    INSTRUMENTS = "instruments"
    SEARCH = "search"

    @property
    def options(self) -> CodecOptions:
        """The layers a song compressed under this scheme is written with.

        ``NONE`` spells every value out as literals, ``RUNS`` writes a held value once,
        ``INSTRUMENTS`` names the phrases the instruments seed at whatever pitch they are played
        at, and ``SEARCH`` adds the phrases the song's own planes repeat.
        """
        match self:
            case CompressionScheme.NONE:
                return CodecOptions(holds=False, phrases=False, transposition=False, search=False)
            case CompressionScheme.RUNS:
                return CodecOptions(holds=True, phrases=False, transposition=False, search=False)
            case CompressionScheme.INSTRUMENTS:
                return CodecOptions(holds=True, phrases=True, transposition=True, search=False)
            case CompressionScheme.SEARCH:
                return EVERY_LAYER


def offered_schemes(seeded: bool) -> Tuple[CompressionScheme, ...]:
    """The schemes worth choosing between for a song, in the order they compress harder.

    ``INSTRUMENTS`` names only the phrases a song's instruments seed, so a song seeding none reads
    the same under it as under ``RUNS`` and is offered the schemes that differ.

    Args:
        seeded: Whether the song's instruments seed the dictionary.

    Returns:
        Tuple[CompressionScheme, ...]: The schemes, from the lightest to the hardest.
    """
    return tuple(scheme for scheme in CompressionScheme if seeded or scheme != CompressionScheme.INSTRUMENTS)
