import pytest

from sampletones_application.ui.panels.sequencer.columns import (
    DIVIDER_TABLE_COLUMN,
    HEADER_TABLE_ROW,
    HEADER_TABLE_ROWS,
    SAMPLE_TABLE_COLUMN,
    TRACKER_TABLE_COLUMNS,
    tracker_table_column,
    tracker_table_row,
)
from sampletones_core.constants.enums import GeneratorName

_CHANNEL_COLUMNS = [
    (GeneratorName.PULSE1, 4),
    (GeneratorName.PULSE2, 5),
    (GeneratorName.TRIANGLE, 6),
    (GeneratorName.NOISE, 7),
]

_PATTERN_ROWS = [(0, 1), (1, 2), (5, 6), (63, 64)]


def test_sample_column_directly_precedes_the_divider() -> None:
    assert tracker_table_column(None) == SAMPLE_TABLE_COLUMN == 2
    assert DIVIDER_TABLE_COLUMN == SAMPLE_TABLE_COLUMN + 1


@pytest.mark.parametrize("generator, expected_column", _CHANNEL_COLUMNS)
def test_channels_sit_one_slot_past_the_divider(generator: GeneratorName, expected_column: int) -> None:
    assert tracker_table_column(generator) == expected_column


def test_no_logical_column_lands_on_the_divider() -> None:
    mapped = {tracker_table_column(None)} | {tracker_table_column(generator) for generator in GeneratorName.items()}

    assert DIVIDER_TABLE_COLUMN not in mapped
    assert len(mapped) == len(GeneratorName.items()) + 1


def test_every_mapped_column_lies_within_the_table() -> None:
    mapped = {tracker_table_column(None)} | {tracker_table_column(generator) for generator in GeneratorName.items()}

    assert DIVIDER_TABLE_COLUMN < TRACKER_TABLE_COLUMNS
    assert max(mapped) < TRACKER_TABLE_COLUMNS


@pytest.mark.parametrize("row_index, expected_row", _PATTERN_ROWS)
def test_pattern_rows_sit_one_slot_past_the_header(row_index: int, expected_row: int) -> None:
    assert tracker_table_row(row_index) == expected_row


def test_no_pattern_row_lands_on_the_header() -> None:
    assert HEADER_TABLE_ROW == 0
    assert tracker_table_row(0) == HEADER_TABLE_ROWS
    assert HEADER_TABLE_ROW not in {tracker_table_row(row_index) for row_index, _ in _PATTERN_ROWS}


def test_row_mapping_preserves_order_and_spacing() -> None:
    mapped = [tracker_table_row(row_index) for row_index in range(8)]

    assert mapped == sorted(mapped)
    assert {second - first for first, second in zip(mapped, mapped[1:])} == {1}
