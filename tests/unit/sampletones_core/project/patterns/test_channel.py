from sampletones_core.constants.enums import ChannelName
from sampletones_core.project.instruments.instrument import Instrument
from sampletones_core.project.patterns.channel import Channel
from sampletones_core.project.patterns.row import Row

ROWS_PER_PATTERN = 16


def _channel() -> Channel:
    return Channel.empty(ChannelName.PULSE1, ROWS_PER_PATTERN)


class TestPatternPool:
    def test_add_pattern_appends_with_requested_length(self) -> None:
        channel = _channel()
        index = channel.add_pattern(8)
        assert index in channel.patterns
        assert channel.pattern(index).length == 8

    def test_clone_pattern_copies_rows_with_new_identity(self) -> None:
        channel = _channel()
        source = channel.patterns[0]
        source.rows[0] = Row(
            instrument=Instrument(sample_id="abc", channel_name=ChannelName.PULSE1),
            volume=10,
        )

        clone_index = channel.clone_pattern(0)
        clone = channel.pattern(clone_index)

        assert clone_index != 0
        assert clone is not source
        assert clone.rows[0] == source.rows[0]

    def test_clone_pattern_avoids_reserved_indices(self) -> None:
        channel = _channel()

        clone_index = channel.clone_pattern(0, reserved_indices={1, 2})

        assert clone_index == 3

    def test_add_pattern_avoids_reserved_indices(self) -> None:
        channel = _channel()

        index = channel.add_pattern(ROWS_PER_PATTERN, reserved_indices={1, 2})

        assert index == 3

    def test_remove_pattern_drops_from_pool(self) -> None:
        channel = _channel()
        extra_index = channel.add_pattern(ROWS_PER_PATTERN)
        channel.remove_pattern(extra_index)
        assert extra_index not in channel.patterns

    def test_set_row_replaces_row(self) -> None:
        channel = _channel()
        pattern_index = 0
        row = Row(transpose=5, volume=12)

        channel.set_row(pattern_index, 3, row)

        assert channel.pattern(pattern_index).rows[3] == row
