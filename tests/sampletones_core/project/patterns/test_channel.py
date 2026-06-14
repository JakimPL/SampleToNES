from sampletones_core.constants.enums import GeneratorName
from sampletones_core.project.instruments.instrument import Instrument
from sampletones_core.project.patterns.channel import Channel
from sampletones_core.project.patterns.row import Row

ROWS_PER_PATTERN = 16


def _channel() -> Channel:
    return Channel.empty(GeneratorName.PULSE1, ROWS_PER_PATTERN)


class TestPatternPool:
    def test_add_pattern_appends_with_requested_length(self) -> None:
        channel = _channel()
        pattern = channel.add_pattern(8)
        assert pattern.length == 8
        assert pattern in channel.patterns

    def test_duplicate_pattern_copies_rows_with_new_identity(self) -> None:
        channel = _channel()
        source = channel.patterns[0]
        source.rows[0] = Row(
            instrument=Instrument(sample_id="abc", generator_name=GeneratorName.PULSE1),
            volume=10,
        )

        clone = channel.duplicate_pattern(source.id)

        assert clone.id != source.id
        assert clone in channel.patterns
        assert clone.rows[0] == source.rows[0]

    def test_remove_pattern_purges_order_references(self) -> None:
        channel = _channel()
        extra = channel.add_pattern(ROWS_PER_PATTERN)
        channel.append_to_order(extra.id)
        channel.append_to_order(extra.id)

        channel.remove_pattern(extra.id)

        assert extra not in channel.patterns
        assert extra.id not in channel.order


class TestOrder:
    def test_order_operations(self) -> None:
        channel = _channel()
        first = channel.order[0]
        second = channel.add_pattern(ROWS_PER_PATTERN)
        channel.append_to_order(second.id)
        assert channel.order == [first, second.id]

        channel.move_in_order(0, 1)
        assert channel.order == [second.id, first]

        channel.remove_from_order(0)
        assert channel.order == [first]

        channel.insert_into_order(0, second.id)
        assert channel.order == [second.id, first]

    def test_set_row_replaces_row(self) -> None:
        channel = _channel()
        pattern_id = channel.order[0]
        row = Row(transpose=5, volume=12)

        channel.set_row(pattern_id, 3, row)

        assert channel.pattern(pattern_id).rows[3] == row
