from sampletones_player.compression.tokens.hold import HoldToken
from sampletones_player.specification.compression import MAX_HOLD_TICKS, OPCODE_SIZE


class TestWhatAHoldCosts:
    """A hold states a count inside its own opcode, so its length is free."""

    def test_a_hold_costs_its_opcode_however_long_it_runs(self) -> None:
        assert HoldToken(ticks=1).size == HoldToken(ticks=MAX_HOLD_TICKS).size == OPCODE_SIZE
