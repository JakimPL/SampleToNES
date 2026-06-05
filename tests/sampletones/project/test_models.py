from dataclasses import dataclass

import pytest
from pydantic import ValidationError

from sampletones_core.constants.enums import GeneratorName
from sampletones_core.project import Row, Subinstrument
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseAutolabelTestCase


def _subinstrument() -> Subinstrument:
    return Subinstrument(instrument_id="abc123", generator_name=GeneratorName.TRIANGLE)


class TestSubinstrument:
    def test_is_frozen(self) -> None:
        subinstrument = _subinstrument()
        with pytest.raises(ValidationError):
            subinstrument.instrument_id = "other"  # type: ignore[misc]

    def test_value_equality_and_hash(self) -> None:
        first = _subinstrument()
        second = _subinstrument()
        assert first == second
        assert hash(first) == hash(second)

    def test_distinct_slices_differ(self) -> None:
        triangle = Subinstrument(instrument_id="abc", generator_name=GeneratorName.TRIANGLE)
        noise = Subinstrument(instrument_id="abc", generator_name=GeneratorName.NOISE)
        assert triangle != noise

    def test_round_trip(self) -> None:
        subinstrument = _subinstrument()
        restored = Subinstrument.model_validate(subinstrument.model_dump())
        assert restored == subinstrument


class TestRowDefaults:
    def test_empty_row(self) -> None:
        row = Row()
        assert row.pitch is None
        assert row.subinstrument is None
        assert row.volume is None

    def test_is_frozen(self) -> None:
        row = Row(pitch=60)
        with pytest.raises(ValidationError):
            row.pitch = 61  # type: ignore[misc]


class TestRowSerialization(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseAutolabelTestCase):
        expected: Row

        @property
        def label(self) -> str:
            return f"pitch={self.expected.pitch}_sub={self.expected.subinstrument is not None}"

    test_cases = [
        TestCase(expected=Row()),
        TestCase(expected=Row(pitch=60, volume=15)),
        TestCase(expected=Row(pitch=48, subinstrument=_subinstrument(), volume=8)),
    ]

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_round_trip(self, test_case: "TestRowSerialization.TestCase") -> None:
        row = test_case.expected
        assert Row.model_validate(row.model_dump()) == row
        assert Row.model_validate_json(row.model_dump_json()) == row
