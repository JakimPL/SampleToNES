from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Final, Generic, Optional, TypeVar

from sampletones_shared.constants.symbols import DOT, HEXADECIMAL, MIXED

KeyT = TypeVar("KeyT")
ValueT = TypeVar("ValueT")

HEXADECIMAL_BASE: Final[int] = 16


@dataclass(frozen=True)
class FieldReading(Generic[ValueT]):
    """What one printed field states about the cell it stands for.

    ``stated`` separates the two readings a value of ``None`` carries: a field printing the dots
    an empty cell shows states emptiness, and one printing the marks a mixed cell shows states
    nothing at all, so its key stays out of the block and a paste passes that cell by.
    """

    value: Optional[ValueT]
    stated: bool

    @classmethod
    def of(cls, value: Optional[ValueT]) -> FieldReading[ValueT]:
        return cls(value=value, stated=True)

    @classmethod
    def mixed(cls) -> FieldReading[ValueT]:
        return cls(value=None, stated=False)


def state_mixed(width: int) -> str:
    """The marks a mixed cell prints, filling its field so every row line reads as a grid."""
    return MIXED * width


def read_placeholder(field: str) -> Optional[FieldReading[ValueT]]:
    """The reading a field of one repeated mark carries: emptiness, or nothing at all.

    Returns:
        The reading, present while the field is dots throughout or marks throughout. A field
        carrying anything else is left to the reader of its own kind.
    """
    marks = set(field)
    if marks == {MIXED}:
        return FieldReading.mixed()

    if marks == {DOT}:
        return FieldReading.of(None)

    return None


def read_hexadecimal(field: str) -> Optional[int]:
    """The number a field of hexadecimal digits names, present while every character is one.

    Digits are read in either case, so a field typed by hand reads as the one the grid prints.
    """
    digits = field.upper()
    if not digits or any(digit not in HEXADECIMAL for digit in digits):
        return None

    return int(digits, HEXADECIMAL_BASE)


def store_reading(
    values: Dict[KeyT, Optional[ValueT]],
    key: KeyT,
    reading: Optional[FieldReading[ValueT]],
) -> bool:
    """Puts the cell a reading states into the map, answering whether the field had a reading.

    A field the form has no reading for answers ``False``, which is what refuses a whole text
    rather than letting one unreadable cell reach the grid.
    """
    if reading is None:
        return False

    if reading.stated:
        values[key] = reading.value

    return True
