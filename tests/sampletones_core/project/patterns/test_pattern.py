import pytest

from sampletones_core.constants.enums import GeneratorName
from sampletones_core.project.instruments.instrument import Instrument
from sampletones_core.project.patterns.pattern import Pattern
from sampletones_core.project.patterns.row import Row

_LENGTH = 4


def _empty_pattern() -> Pattern:
    return Pattern.empty(_LENGTH)


def _row_with_instrument() -> Row:
    return Row(instrument=Instrument(sample_id="x", generator_name=GeneratorName.PULSE1))


class TestRowIsEmpty:
    def test_default_row_is_empty(self) -> None:
        assert Row().is_empty()

    def test_row_with_instrument_is_not_empty(self) -> None:
        assert not Row(instrument=Instrument(sample_id="x", generator_name=GeneratorName.PULSE1)).is_empty()

    def test_row_with_transpose_is_not_empty(self) -> None:
        assert not Row(transpose=0).is_empty()

    def test_row_with_volume_is_not_empty(self) -> None:
        assert not Row(volume=15).is_empty()


class TestPatternIsEmpty:
    def test_freshly_created_pattern_is_empty(self) -> None:
        assert _empty_pattern().is_empty()

    def test_pattern_with_one_filled_row_is_not_empty(self) -> None:
        pattern = _empty_pattern()
        pattern.rows[0] = _row_with_instrument()

        assert not pattern.is_empty()

    def test_pattern_with_all_filled_rows_is_not_empty(self) -> None:
        pattern = _empty_pattern()
        for i in range(_LENGTH):
            pattern.rows[i] = _row_with_instrument()

        assert not pattern.is_empty()
