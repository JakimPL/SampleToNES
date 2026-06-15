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
        index = channel.add_pattern(8)
        assert index in channel.patterns
        assert channel.pattern(index).length == 8

    def test_duplicate_pattern_copies_rows_with_new_identity(self) -> None:
        channel = _channel()
        source = channel.patterns[0]
        source.rows[0] = Row(
            instrument=Instrument(sample_id="abc", generator_name=GeneratorName.PULSE1),
            volume=10,
        )

        clone_index = channel.duplicate_pattern(0)
        clone = channel.pattern(clone_index)

        assert clone_index != 0
        assert clone is not source
        assert clone.rows[0] == source.rows[0]

    def test_remove_pattern_empties_referencing_slots_without_shifting(self) -> None:
        channel = _channel()
        extra_index = channel.add_pattern(ROWS_PER_PATTERN)
        channel.append_to_order(extra_index)
        channel.append_to_order(extra_index)

        channel.remove_pattern(extra_index)

        assert extra_index not in channel.patterns
        assert channel.order == [0, None, None]

    def test_reusing_a_removed_index_does_not_refill_emptied_slots(self) -> None:
        channel = _channel()
        extra_index = channel.add_pattern(ROWS_PER_PATTERN)
        channel.append_to_order(extra_index)
        channel.remove_pattern(extra_index)

        reused_index = channel.add_pattern(ROWS_PER_PATTERN)

        assert reused_index == extra_index
        assert channel.order == [0, None]


class TestOrder:
    def test_order_operations(self) -> None:
        channel = _channel()
        first = channel.order[0]
        second_index = channel.add_pattern(ROWS_PER_PATTERN)
        channel.append_to_order(second_index)
        assert channel.order == [first, second_index]

        channel.move_in_order(0, 1)
        assert channel.order == [second_index, first]

        channel.remove_from_order(0)
        assert channel.order == [first]

        channel.insert_into_order(0, second_index)
        assert channel.order == [second_index, first]

    def test_set_row_replaces_row(self) -> None:
        channel = _channel()
        pattern_index = channel.order[0]
        row = Row(transpose=5, volume=12)

        channel.set_row(pattern_index, 3, row)

        assert channel.pattern(pattern_index).rows[3] == row
