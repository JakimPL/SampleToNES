from __future__ import annotations

from typing import Dict, Final, Tuple

from pydantic import BaseModel, ConfigDict, model_validator

from sampletones_player.specification.binary import MAX_BYTE_VALUE, WORD_SIZE
from sampletones_tools.codec.study.packing.form import SINGLE_TICK

TABLE_LENGTH_SIZE: Final[int] = 1
TABLE_OFFSET_SIZE: Final[int] = WORD_SIZE


class TableForm(BaseModel):
    """A plane's distinct values gathered into a table, its byte naming one of them and a count.

    A mask frees only the bits a register leaves alone, and a plane playing a handful of values
    spread across its byte frees none — a triangle channel sounding or resting turns over seven
    bits to say one thing. Listing what the plane plays gives every such plane a short code, and
    the bits the code leaves carry the repeat count.

    The code is the value's place in the table, so the table leads with the value the plane is
    seeded to and the driver reaches a register byte by one indexed load.

    Attributes:
        values: The register byte each code stands for, in code order.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    values: Tuple[int, ...]

    @model_validator(mode="after")
    def _validate_the_table_names_each_value_once(self) -> TableForm:
        if not self.values:
            raise ValueError("a table names at least one value")

        if len(set(self.values)) != len(self.values):
            raise ValueError("a table names each value once, and this one repeats a value")

        outside = tuple(value for value in self.values if not 0 <= value <= MAX_BYTE_VALUE)
        if outside:
            raise ValueError(f"a table names register bytes, and it names {outside}")

        return self

    @classmethod
    def across(cls, plane: bytes) -> TableForm:
        """The table a plane's own values fill, in the order they sound from quietest upward.

        Args:
            plane: The values the plane plays.

        Returns:
            TableForm: The table.
        """
        return cls(values=tuple(sorted(set(plane))))

    @property
    def code_bits(self) -> int:
        """The bits a code takes."""
        return (len(self.values) - 1).bit_length()

    @property
    def value_mask(self) -> int:
        """The bits the code occupies."""
        return (1 << self.code_bits) - 1

    @property
    def count_mask(self) -> int:
        """The bits a repeat count occupies."""
        return MAX_BYTE_VALUE ^ self.value_mask

    @property
    def count_step(self) -> int:
        """What one further repeat adds to a symbol."""
        return 1 << self.code_bits

    @property
    def repeats(self) -> int:
        """The ticks one symbol covers at most."""
        return self.count_mask // self.count_step + 1 if self.count_mask else SINGLE_TICK

    @property
    def counts(self) -> bool:
        """Whether the plane's byte has room to count a repeat."""
        return self.repeats > SINGLE_TICK

    @property
    def seeded(self) -> int:
        """The register byte the plane stands at before its first token."""
        return self.values[0]

    @property
    def stated(self) -> int:
        """The bytes the song block takes to state the table."""
        return TABLE_OFFSET_SIZE + TABLE_LENGTH_SIZE + len(self.values)

    def symbol(self, value: int, repeats: int) -> int:
        """The byte the plane writes for ``value`` sounding ``repeats`` ticks running.

        Args:
            value: The register byte the ticks play.
            repeats: The ticks the value sounds for.

        Returns:
            int: The symbol.

        Raises:
            ValueError: If the table names no such value, or the repeats reach past what one
                symbol counts.
        """
        if not SINGLE_TICK <= repeats <= self.repeats:
            raise ValueError(f"one symbol counts {SINGLE_TICK} through {self.repeats} ticks, and this counts {repeats}")

        return self._codes[value] | (repeats - SINGLE_TICK) * self.count_step

    def value(self, symbol: int) -> int:
        """The register byte ``symbol`` plays."""
        return self.values[symbol & self.value_mask]

    def repeated(self, symbol: int) -> int:
        """The ticks ``symbol`` covers."""
        if not self.count_mask:
            return SINGLE_TICK

        return (symbol & self.count_mask) // self.count_step + SINGLE_TICK

    def idles(self, plane: bytes) -> bool:
        """Whether the plane holds the value it is seeded to throughout, so it takes no stream.

        Args:
            plane: The values the plane plays.

        Returns:
            bool: Whether the plane leaves its seeded value.
        """
        return set(plane) <= {self.seeded}

    @property
    def _codes(self) -> Dict[int, int]:
        return {value: code for code, value in enumerate(self.values)}
