from __future__ import annotations

from typing import Final

from pydantic import BaseModel, ConfigDict, Field, model_validator

from sampletones_player.specification.binary import MAX_BYTE_VALUE

SINGLE_TICK: Final[int] = 1
NO_BITS: Final[int] = 0


class PlaneForm(BaseModel):
    """How a plane's byte divides between the value its register reads and a repeat count.

    A channel's register reads some of a byte's bits and ignores the rest: a pulse channel's
    volume is four bits under two the hardware wants set, and a noise period is four bits with
    three above it that say nothing. A plane writes its value in the bits that reach the register
    and counts the ticks that value repeats for in the ones left over, so a run costs one byte
    however long it rests.

    The division is a mask, which is what keeps the reading cheap: the register byte is the
    symbol masked and ored with the bits the hardware fixes, and one repeat is a subtraction of
    ``count_step``. A plane whose values need every bit states a full ``value_mask``, carries no
    count, and reads byte for byte as it does today.

    Attributes:
        value_mask: The bits the value occupies.
        value_or: The bits the register fixes, which every value of the plane carries.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    value_mask: int = Field(..., ge=0, le=MAX_BYTE_VALUE)
    value_or: int = Field(..., ge=0, le=MAX_BYTE_VALUE)

    @model_validator(mode="after")
    def _validate_the_fixed_bits_lie_outside_the_value(self) -> PlaneForm:
        if self.value_or & self.value_mask:
            raise ValueError(
                f"the bits a register fixes lie outside the value's own, and {self.value_or:#04x} "
                f"meets {self.value_mask:#04x}"
            )

        return self

    @model_validator(mode="after")
    def _validate_the_count_occupies_one_run_of_bits(self) -> PlaneForm:
        if not self.count_mask:
            return self

        counted = self.count_mask // self.count_step
        if counted & (counted + 1):
            raise ValueError(
                f"a repeat count occupies one run of bits, and the value breaks {self.count_mask:#04x} apart"
            )

        return self

    @property
    def count_mask(self) -> int:
        """The bits a repeat count occupies."""
        return MAX_BYTE_VALUE ^ self.value_mask

    @property
    def count_step(self) -> int:
        """What one further repeat adds to a symbol."""
        return self.count_mask & -self.count_mask

    @property
    def repeats(self) -> int:
        """The ticks one symbol covers at most."""
        if not self.count_mask:
            return SINGLE_TICK

        return self.count_mask // self.count_step + 1

    @property
    def counts(self) -> bool:
        """Whether the plane's byte has room to count a repeat."""
        return self.repeats > SINGLE_TICK

    def symbol(self, value: int, repeats: int) -> int:
        """The byte a plane writes for ``value`` sounding ``repeats`` ticks running.

        Args:
            value: The register byte the ticks play.
            repeats: The ticks the value sounds for, up to ``repeats``.

        Returns:
            int: The symbol.

        Raises:
            ValueError: If the value carries fixed bits other than the form's, or the repeats
                reach past what one symbol counts.
        """
        if value & self.count_mask != self.value_or:
            raise ValueError(
                f"a value of this plane carries {self.value_or:#04x} in the bits the count takes, "
                f"and {value:#04x} carries {value & self.count_mask:#04x}"
            )

        if not SINGLE_TICK <= repeats <= self.repeats:
            raise ValueError(f"one symbol counts {SINGLE_TICK} through {self.repeats} ticks, and this counts {repeats}")

        return (value & self.value_mask) | (repeats - SINGLE_TICK) * self.count_step

    def value(self, symbol: int) -> int:
        """The register byte ``symbol`` plays."""
        return (symbol & self.value_mask) | self.value_or

    def repeated(self, symbol: int) -> int:
        """The ticks ``symbol`` covers."""
        if not self.count_mask:
            return SINGLE_TICK

        return (symbol & self.count_mask) // self.count_step + SINGLE_TICK

    @property
    def seeded(self) -> int:
        """The register byte a plane stands at before its first token.

        The driver seeds every plane to the value zero states, which under a form is the bits the
        register fixes: a pulse channel's control byte seeds to a sustained silence rather than to
        nothing at all. A plane holding that value throughout therefore takes no stream.
        """
        return self.value(NO_BITS)

    def idles(self, plane: bytes) -> bool:
        """Whether the plane holds the value it is seeded to throughout, so it takes no stream.

        Args:
            plane: The values the plane plays.

        Returns:
            bool: Whether the plane leaves its seeded value.
        """
        return set(plane) <= {self.seeded}

    def fits(self, plane: bytes) -> bool:
        """Whether every value the plane plays carries the bits this form fixes.

        Args:
            plane: The values the plane plays.

        Returns:
            bool: Whether the form reads the plane.
        """
        return all(value & self.count_mask == self.value_or for value in plane)


WHOLE_BYTE: Final[PlaneForm] = PlaneForm(value_mask=MAX_BYTE_VALUE, value_or=NO_BITS)
