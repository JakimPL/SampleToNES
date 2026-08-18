from dataclasses import dataclass

import pytest

from sampletones_core.formats.bitphase.identifiers import format_instrument_id
from sampletones_core.formats.bitphase.specification.instruments import (
    INSTRUMENT_ID_DIGITS,
    MAX_INSTRUMENT_ID,
    MIN_INSTRUMENT_ID,
)
from sampletones_core.formats.bitphase.specification.patterns import SYMBOL_BASE
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase


@dataclass
class IdentifierCase:
    number: int
    identifier: str


class TestFormatInstrumentId(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class IdentifierCase(BaseRegularTestCase):
        number: int
        identifier: str

    test_cases = (
        IdentifierCase(number=1, identifier="01", label="1"),
        IdentifierCase(number=10, identifier="0A", label="10"),
        IdentifierCase(number=35, identifier="0Z", label="35"),
        IdentifierCase(number=36, identifier="10", label="36"),
        IdentifierCase(
            number=MAX_INSTRUMENT_ID,
            identifier="ZZ",
            label=str(MAX_INSTRUMENT_ID),
        ),
    )

    @pytest.mark.parametrize("case", test_cases, ids=lambda case: case.label)
    def test_a_number_renders_as_its_base36_text(self, case: IdentifierCase) -> None:
        assert format_instrument_id(case.number) == case.identifier

    def test_bitphase_parses_the_written_text_back(self) -> None:
        """A pattern's instrument column is matched against ``parseInt(id, 36)``, so the
        text has to read back as the number the column carries.
        """
        for number in range(MIN_INSTRUMENT_ID, MAX_INSTRUMENT_ID + 1):
            assert int(format_instrument_id(number), SYMBOL_BASE) == number

    def test_every_identifier_fills_the_column(self) -> None:
        widths = {
            len(format_instrument_id(number))
            for number in range(
                MIN_INSTRUMENT_ID,
                MAX_INSTRUMENT_ID + 1,
            )
        }
        assert widths == {INSTRUMENT_ID_DIGITS}
