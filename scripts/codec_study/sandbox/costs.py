from dataclasses import dataclass
from typing import Final

from sampletones_player.compression.dictionary.table import PhraseTable
from sampletones_player.compression.tokens.sizes import hold_size
from sampletones_player.specification.compression import (
    CHEAP_PHRASE_IDS,
    OPCODE_SIZE,
    PHRASE_COUNT_SIZE,
    PHRASE_ESCAPE_SIZE,
    TRANSPOSE_SIZE,
)

VALUE_SIZE: Final[int] = 1
DEFAULT_COUNT_SIZE: Final[int] = 1
DEFAULT_FLAG_BITS: Final[int] = 1


@dataclass(frozen=True)
class Costs:
    """The bytes each token takes under one grammar.

    A token on the free escape is a phrase opcode followed by a count of zero, which the codec
    as it stands never writes, so the opcode's operand is what such a token carries: the sizes
    it counts are as many as the cheap ids a phrase opcode names.

    Attributes:
        opcode: The bytes an opcode takes.
        hold: The bytes a hold takes.
        wide_hold: The bytes a wide hold takes.
        set_hold: The bytes a set-hold takes.
        phrase_count: The bytes a phrase token's count takes.
        phrase_escape: The bytes naming a phrase beyond the cheap ids takes.
        transpose: The bytes a shift takes.
        operands: The operand values below the escape: the cheap ids a phrase opcode names, and
            the sizes a token on the escape counts.
        default_entry: The bytes a table entry grows by to carry the phrase's default count.
    """

    opcode: int
    hold: int
    wide_hold: int
    set_hold: int
    phrase_count: int
    phrase_escape: int
    transpose: int
    operands: int
    default_entry: int

    def literal(self, length: int) -> int:
        """The bytes a literal of ``length`` values takes."""
        return self.opcode + length

    def phrase(
        self,
        phrase_id: int,
        transpose: int,
        *,
        default: bool,
    ) -> int:
        """The bytes a token playing a phrase takes.

        Args:
            phrase_id: Position the phrase takes in the table.
            transpose: The shift every byte of the phrase is played at.
            default: Whether the token plays the phrase's default count and carries none.

        Returns:
            int: The bytes the token takes.
        """
        escape = self.phrase_escape if phrase_id >= self.operands else 0
        count = 0 if default else self.phrase_count
        shift = self.transpose if transpose else 0
        return self.opcode + escape + count + shift

    def dictionary(self, table: PhraseTable) -> int:
        """The bytes ``table`` takes in the song block under this grammar."""
        return table.size + self.default_entry * len(table)


PRODUCTION_COSTS: Final[Costs] = Costs(
    opcode=OPCODE_SIZE,
    hold=hold_size(),
    wide_hold=OPCODE_SIZE + PHRASE_COUNT_SIZE,
    set_hold=OPCODE_SIZE + PHRASE_COUNT_SIZE + VALUE_SIZE,
    phrase_count=PHRASE_COUNT_SIZE,
    phrase_escape=PHRASE_ESCAPE_SIZE,
    transpose=TRANSPOSE_SIZE,
    operands=CHEAP_PHRASE_IDS,
    default_entry=0,
)
SET_HOLD_BOUND: Final[int] = OPCODE_SIZE + VALUE_SIZE
DEFAULT_COUNT_OPERANDS: Final[int] = (CHEAP_PHRASE_IDS + 1) // (1 << DEFAULT_FLAG_BITS) - 1
