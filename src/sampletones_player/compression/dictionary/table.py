from __future__ import annotations

from typing import Iterable, Set, Tuple

from pydantic import BaseModel, ConfigDict, model_validator

from sampletones_player.compression.dictionary.phrase import Phrase
from sampletones_player.specification.compression import (
    MAX_PHRASE_IDS,
    PHRASE_TABLE_COUNT_SIZE,
)


class PhraseTable(BaseModel):
    """The dictionary a song's tokens name, in the order the song block writes it.

    A phrase's position is its id, and the cheap ids ride inside a token's opcode, so the order
    is part of the encoding: the phrases a song leans on hardest take the ids that cost least.

    Attributes:
        phrases: The phrases, in id order.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    phrases: Tuple[Phrase, ...]

    @model_validator(mode="after")
    def _validate_the_table_fits_the_ids_a_token_reaches(self) -> PhraseTable:
        if len(self.phrases) > MAX_PHRASE_IDS:
            raise ValueError(f"a token names one of {MAX_PHRASE_IDS} phrases, and the table holds {len(self.phrases)}")

        return self

    def __len__(self) -> int:
        return len(self.phrases)

    def __getitem__(self, phrase_id: int) -> Phrase:
        return self.phrases[phrase_id]

    @property
    def size(self) -> int:
        """The bytes the whole dictionary takes in the song block."""
        return PHRASE_TABLE_COUNT_SIZE + sum(phrase.size for phrase in self.phrases)


def phrase_table(phrases: Iterable[Phrase]) -> PhraseTable:
    """Collects phrases into a table, each shape kept once and the ids capped at what fits.

    Args:
        phrases: The phrases to hold, in the order they are preferred.

    Returns:
        PhraseTable: The table, holding as many of them as a token can name.
    """
    collected: Tuple[Phrase, ...] = ()
    seen: Set[bytes] = set()
    for phrase in phrases:
        if phrase.body in seen or len(collected) == MAX_PHRASE_IDS:
            continue

        seen.add(phrase.body)
        collected += (phrase,)

    return PhraseTable(phrases=collected)
