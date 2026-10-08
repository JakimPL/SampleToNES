import pytest

from sampletones_application.ui.panels.sequencer.columns import (
    DIVIDER_TABLE_COLUMN,
    SAMPLE_TABLE_COLUMN,
    TRACKER_TABLE_COLUMNS,
    tracker_table_column,
)
from sampletones_core.constants.enums import ChannelName

_CHANNEL_COLUMNS = [
    (ChannelName.PULSE1, 4),
    (ChannelName.PULSE2, 5),
    (ChannelName.TRIANGLE, 6),
    (ChannelName.NOISE, 7),
]


def test_sample_column_directly_precedes_the_divider() -> None:
    assert tracker_table_column(None) == SAMPLE_TABLE_COLUMN == 2
    assert DIVIDER_TABLE_COLUMN == SAMPLE_TABLE_COLUMN + 1


@pytest.mark.parametrize("channel, expected_column", _CHANNEL_COLUMNS)
def test_channels_sit_one_slot_past_the_divider(channel: ChannelName, expected_column: int) -> None:
    assert tracker_table_column(channel) == expected_column


def test_no_logical_column_lands_on_the_divider() -> None:
    mapped = {tracker_table_column(None)} | {tracker_table_column(channel) for channel in ChannelName.items()}

    assert DIVIDER_TABLE_COLUMN not in mapped
    assert len(mapped) == len(ChannelName.items()) + 1


def test_every_mapped_column_lies_within_the_table() -> None:
    mapped = {tracker_table_column(None)} | {tracker_table_column(channel) for channel in ChannelName.items()}

    assert DIVIDER_TABLE_COLUMN < TRACKER_TABLE_COLUMNS
    assert max(mapped) < TRACKER_TABLE_COLUMNS
