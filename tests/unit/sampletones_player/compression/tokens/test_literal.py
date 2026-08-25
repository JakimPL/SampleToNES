from sampletones_player.compression.tokens.literal import LiteralToken
from sampletones_player.compression.tokens.sizes import literal_size
from sampletones_player.specification.compression import OPCODE_SIZE

SPELLED_OUT: int = 5


class TestWhatALiteralCosts:
    """A literal spells its values out, so it costs its opcode and every one of them."""

    def test_a_literal_covers_a_tick_for_every_value_it_states(self) -> None:
        assert LiteralToken(values=bytes(SPELLED_OUT)).ticks == SPELLED_OUT

    def test_a_literal_costs_its_opcode_and_the_values_it_spells_out(self) -> None:
        token = LiteralToken(values=bytes(SPELLED_OUT))
        assert token.size == literal_size(SPELLED_OUT) == OPCODE_SIZE + SPELLED_OUT
