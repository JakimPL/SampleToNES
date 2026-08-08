from typing import Optional

from sampletones_application.ui.panels.sequencer.input.order import (
    ORDER_ROWS,
    OrderCursor,
    OrderInputState,
)
from sampletones_core.constants.enums import GeneratorName


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
        state = OrderInputState(cursor=OrderCursor(ORDER_ROWS[0], 0))
        for _ in range(len(ORDER_ROWS)):
            visited.append(state.cursor.generator)
            state = state.navigate_channel(1)

        assert visited == list(ORDER_ROWS)
        assert state.cursor.generator == ORDER_ROWS[0]


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
