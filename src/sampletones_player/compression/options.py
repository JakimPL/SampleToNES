from dataclasses import dataclass
from typing import Final


@dataclass(frozen=True)
class CodecOptions:
    """Which of the codec's layers an encoding is built from.

    Every layer earns its place on measured ground, so each is switched on its own and a report
    reads the bytes each one saves. Literals carry any plane on their own, so an encoding with
    every layer off still describes the song.

    Attributes:
        holds: Whether a run of one value reaches the stream as a hold.
        phrases: Whether tokens name phrases from the dictionary.
        transposition: Whether a phrase is played shifted, one entry serving every pitch a note
            is played at.
        search: Whether the encoder looks for phrases beyond the ones the instruments seed.
    """

    holds: bool
    phrases: bool
    transposition: bool
    search: bool


EVERY_LAYER: Final[CodecOptions] = CodecOptions(
    holds=True,
    phrases=True,
    transposition=True,
    search=True,
)
