from dataclasses import dataclass

import pytest
from pydantic import ValidationError

from sampletones_core.constants.enums import GeneratorName
from sampletones_core.project.instruments.instrument import Instrument
from sampletones_core.project.instruments.note_off import NoteOff
from sampletones_core.project.patterns.row import Row
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseAutolabelTestCase


def _instrument() -> Instrument:
    return Instrument(
        sample_id="abc123",
        generator_name=GeneratorName.TRIANGLE,
    )


class TestInstrument:
    def test_is_frozen(self) -> None:
        instrument = _instrument()
        with pytest.raises(ValidationError):
            instrument.sample_id = "other"  # type: ignore[misc]

    def test_value_equality_and_hash(self) -> None:
        first = _instrument()
        second = _instrument()
        assert first == second
        assert hash(first) == hash(second)

    def test_distinct_slices_differ(self) -> None:
        triangle = Instrument(sample_id="abc", generator_name=GeneratorName.TRIANGLE)
        noise = Instrument(sample_id="abc", generator_name=GeneratorName.NOISE)
        assert triangle != noise

    def test_round_trip(self) -> None:
        instrument = _instrument()
        restored = Instrument.model_validate(instrument.model_dump())
        assert restored == instrument


class TestRowDefaults:
    def test_empty_row(self) -> None:
        row = Row()
        assert row.transpose is None
        assert row.command is None
        assert row.volume is None

    def test_is_frozen(self) -> None:
        row = Row(transpose=12)
        with pytest.raises(ValidationError):
            row.transpose = 13  # type: ignore[misc]


class TestRowSerialization(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseAutolabelTestCase):
        expected: Row

        @property
        def label(self) -> str:
            return f"transpose={self.expected.transpose}_command={self.expected.command is not None}"

    test_cases = (
        TestCase(expected=Row()),
        TestCase(expected=Row(transpose=0, volume=15)),
        TestCase(expected=Row(transpose=12, command=_instrument(), volume=8)),
        TestCase(expected=Row(command=NoteOff())),
    )

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_round_trip(self, test_case: TestCase) -> None:
        row = test_case.expected
        assert Row.model_validate(row.model_dump()) == row
        assert Row.model_validate_json(row.model_dump_json()) == row
