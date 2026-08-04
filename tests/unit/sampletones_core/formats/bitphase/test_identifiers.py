from dataclasses import dataclass
from typing import List

import pytest

from sampletones_core.formats.bitphase.identifiers import format_instrument_id
from sampletones_core.formats.bitphase.specification.instruments import (
    INSTRUMENT_ID_DIGITS,
    MAX_INSTRUMENT_ID,
    MIN_INSTRUMENT_ID,
)
from sampletones_core.formats.bitphase.specification.patterns import SYMBOL_BASE


@dataclass
class IdentifierCase:
    number: int
    identifier: str


IDENTIFIER_CASES: List[IdentifierCase] = [
    IdentifierCase(number=1, identifier="01"),
    IdentifierCase(number=10, identifier="0A"),
    IdentifierCase(number=35, identifier="0Z"),
    IdentifierCase(number=36, identifier="10"),
    IdentifierCase(number=MAX_INSTRUMENT_ID, identifier="ZZ"),
]


class TestFormatInstrumentId:
    @pytest.mark.parametrize("case", IDENTIFIER_CASES, ids=lambda case: str(case.number))
    def test_a_number_renders_as_its_base36_text(self, case: IdentifierCase) -> None:
        assert format_instrument_id(case.number) == case.identifier

    def test_bitphase_parses_the_written_text_back(self) -> None:
        """A pattern's instrument column is matched against ``parseInt(id, 36)``, so the
        text has to read back as the number the column carries.
        """
        for number in range(MIN_INSTRUMENT_ID, MAX_INSTRUMENT_ID + 1):
            assert int(format_instrument_id(number), SYMBOL_BASE) == number

    def test_every_identifier_fills_the_column(self) -> None:
        widths = {len(format_instrument_id(number)) for number in range(MIN_INSTRUMENT_ID, MAX_INSTRUMENT_ID + 1)}
        assert widths == {INSTRUMENT_ID_DIGITS}
