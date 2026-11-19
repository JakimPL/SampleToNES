import pytest

from sampletones_player.specification.binary import BYTE_VALUES, MAX_BYTE_VALUE, byte_steps


class TestByteSteps:
    """The steps between neighboring bytes wrap around the byte's range, so a ramp across the top
    reads as one constant step."""

    @pytest.mark.parametrize("data", [b"", bytes((7,))], ids=["empty", "one byte"])
    def test_fewer_than_two_bytes_take_no_step(self, data: bytes) -> None:
        assert byte_steps(data) == b""

    def test_a_rise_and_a_fall(self) -> None:
        assert byte_steps(bytes((10, 13, 11))) == bytes((3, BYTE_VALUES - 2))

    def test_a_ramp_across_the_top_wraps_to_one_step(self) -> None:
        assert byte_steps(bytes((MAX_BYTE_VALUE - 1, MAX_BYTE_VALUE, 0, 1))) == bytes((1, 1, 1))

    def test_a_held_value_steps_by_zero(self) -> None:
        assert byte_steps(bytes((5, 5, 5))) == bytes((0, 0))

    def test_a_step_from_zero_to_the_top_is_the_widest(self) -> None:
        assert byte_steps(bytes((0, MAX_BYTE_VALUE))) == bytes((MAX_BYTE_VALUE,))
