from dataclasses import dataclass

from sampletones_player.compression.tokens.sizes import phrase_size


@dataclass(frozen=True)
class PhraseToken:
    """The plane plays a phrase from the table, shifted by ``transpose``, for ``ticks`` ticks.

    A count past the phrase's own length holds its final value onwards, the way a note whose
    envelope has finished keeps sounding, and a count short of it cuts the note off.
    """

    phrase_id: int
    ticks: int
    transpose: int

    @property
    def size(self) -> int:
        """The bytes the token takes."""
        return phrase_size(self.phrase_id, self.transpose)
