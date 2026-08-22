from sampletones_player.compression.matches.shift import translation
from sampletones_player.specification.compression import BYTE_VALUES

MOTIF: bytes = bytes((40, 44, 47))


class TestAShiftMovesEveryValueOfAPhrase:
    """The driver adds the shift to a byte, so the encoder agrees with it byte for byte."""

    def test_a_rise_moves_every_value_up(self) -> None:
        assert MOTIF.translate(translation(5)) == bytes(value + 5 for value in MOTIF)

    def test_a_fall_reaches_a_phrase_as_the_byte_that_wraps_to_it(self) -> None:
        assert MOTIF.translate(translation(BYTE_VALUES - 3)) == bytes(value - 3 for value in MOTIF)

    def test_the_shift_a_phrase_is_stored_at_leaves_it_alone(self) -> None:
        assert MOTIF.translate(translation(0)) == MOTIF
