from __future__ import annotations

from pydantic import BaseModel, ConfigDict, model_validator

from sampletones_player.specification.compression import (
    BYTE_VALUES,
    MAX_PHRASE_LENGTH,
    PHRASE_LENGTH_SIZE,
    PHRASE_TABLE_ENTRY_SIZE,
)


class Phrase(BaseModel):
    """One entry of the dictionary: the values a plane plays when a token names it.

    A phrase is stored at the pitch it was found at, and a token states the shift it is played
    at, so a note's shape is written once and every pitch it sounds at names that one entry.

    Attributes:
        body: The values the phrase plays, one per tick.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    body: bytes

    @model_validator(mode="after")
    def _validate_the_body_fits_a_table_entry(self) -> Phrase:
        if not 1 <= len(self.body) <= MAX_PHRASE_LENGTH:
            raise ValueError(f"a phrase runs from 1 to {MAX_PHRASE_LENGTH} values, and this one runs {len(self.body)}")

        return self

    @property
    def length(self) -> int:
        """The ticks the phrase's own values cover."""
        return len(self.body)

    @property
    def differences(self) -> bytes:
        """The step from each value to the next, which is the shape a shift leaves alone."""
        return bytes((following - value) % BYTE_VALUES for value, following in zip(self.body, self.body[1:]))

    @property
    def size(self) -> int:
        """The bytes the phrase takes in the song block, its table entry included."""
        return PHRASE_TABLE_ENTRY_SIZE + PHRASE_LENGTH_SIZE + len(self.body)
