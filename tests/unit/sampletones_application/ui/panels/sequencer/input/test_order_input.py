from typing import Optional

from sampletones_application.constants.sequencer import CHANNEL_AXIS
from sampletones_application.ui.panels.sequencer.input.order import (
    OrderCursor,
    OrderInputState,
)
from sampletones_core.constants.enums import GeneratorName

POSITION_COUNT = 8


def _state(
    generator: Optional[GeneratorName] = GeneratorName.PULSE1,
    position: int = 0,
    pending: str = "",
) -> OrderInputState:
    return OrderInputState(cursor=OrderCursor(generator, position), pending=pending)


class TestNavigation:
    def test_position_clamps_within_bounds(self) -> None:
        state = _state(position=2)
        assert state.navigate_position(5, position_count=4).cursor.position == 3
        assert state.navigate_position(-5, position_count=4).cursor.position == 0

    def test_position_absolute_jump(self) -> None:
        assert _state(position=0).navigate_position(3, position_count=4, absolute=True).cursor.position == 3

    def test_position_is_a_no_op_without_positions(self) -> None:
        state = _state()
        assert state.navigate_position(1, position_count=0) is state

    def test_channel_cycles_master_then_channels_and_wraps(self) -> None:
        visited = []
        state = OrderInputState(cursor=OrderCursor(CHANNEL_AXIS[0], 0))
        for _ in range(len(CHANNEL_AXIS)):
            visited.append(state.cursor.generator)
            state = state.navigate_channel(1)

        assert visited == list(CHANNEL_AXIS)
        assert state.cursor.generator == CHANNEL_AXIS[0]


class TestSelection:
    """Shift-extended moves grow a region from the cell the selection was started on."""

    def test_a_state_without_an_anchor_covers_no_region(self) -> None:
        assert _state().region is None

    def test_the_first_extend_anchors_the_cell_it_came_from(self) -> None:
        extended = _state(position=2).extend_position(1, POSITION_COUNT)

        region = extended.region
        assert region is not None
        assert (region.first_position, region.last_position) == (2, 3)
        assert region.position_count == 2

    def test_extending_leftwards_names_the_same_region_as_rightwards(self) -> None:
        leftwards = _state(position=3).extend_position(-1, POSITION_COUNT).region
        rightwards = _state(position=2).extend_position(1, POSITION_COUNT).region

        assert leftwards == rightwards

    def test_extending_channels_reaches_from_master_down(self) -> None:
        extended = _state(generator=None).extend_channel(2)

        region = extended.region
        assert region is not None
        assert region.generators == (None, GeneratorName.PULSE1, GeneratorName.PULSE2)

    def test_extending_channels_stops_at_either_end_of_the_axis(self) -> None:
        """A selection covers a run of the table, so its reach stops where plain navigation wraps."""
        first = _state(generator=CHANNEL_AXIS[0]).extend_channel(-1)
        last = _state(generator=CHANNEL_AXIS[-1]).extend_channel(1)

        assert first.cursor == OrderCursor(CHANNEL_AXIS[0], 0)
        assert last.cursor == OrderCursor(CHANNEL_AXIS[-1], 0)

    def test_a_plain_move_collapses_the_selection(self) -> None:
        moved = _state(position=1).extend_position(2, POSITION_COUNT).navigate_position(1, POSITION_COUNT)

        assert moved.anchor is None
        assert moved.region is None

    def test_a_plain_channel_move_collapses_the_selection(self) -> None:
        moved = _state().extend_position(1, POSITION_COUNT).navigate_channel(1)

        assert moved.region is None

    def test_dropping_a_partial_entry_holds_the_selection(self) -> None:
        held = _state(pending="5").extend_position(1, POSITION_COUNT).reset_pending()

        assert held.region is not None

    def test_typing_an_index_collapses_the_selection(self) -> None:
        selected = _state(position=1).extend_position(2, POSITION_COUNT)

        partial, first = selected.type_char("0")
        committed, index = partial.type_char("2")

        assert first is None
        assert index == 2
        assert committed.region is None

    def test_cancel_drops_the_selection_and_the_partial_entry(self) -> None:
        cancelled = _state(pending="5").extend_position(1, POSITION_COUNT).cancel()

        assert cancelled.region is None
        assert cancelled.pending == ""


class TestEntry:
    def test_type_char_commits_after_two_digits(self) -> None:
        partial, first = _state().type_char("A")
        assert first is None
        assert partial.pending == "A"

        committed, index = partial.type_char("F")
        assert index == 0xAF
        assert committed.pending == ""

    def test_commit_partial_pads_a_single_digit(self) -> None:
        committed, index = _state(pending="5").commit_partial()
        assert index == 5
        assert committed.pending == ""

    def test_commit_partial_is_a_no_op_without_pending(self) -> None:
        state = _state()
        committed, index = state.commit_partial()
        assert index is None
        assert committed is state

    def test_cancel_clears_pending(self) -> None:
        assert _state(pending="3").cancel().pending == ""
