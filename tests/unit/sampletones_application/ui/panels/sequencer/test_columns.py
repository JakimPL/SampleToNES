import pytest

from sampletones_application.ui.panels.sequencer.columns import (
    DIVIDER_TABLE_COLUMN,
    SAMPLE_TABLE_COLUMN,
    tracker_table_column,
)
from sampletones_core.constants.enums import GeneratorName

_CHANNEL_COLUMNS = [
    (GeneratorName.PULSE1, 4),
    (GeneratorName.PULSE2, 5),
    (GeneratorName.TRIANGLE, 6),
    (GeneratorName.NOISE, 7),
]


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
