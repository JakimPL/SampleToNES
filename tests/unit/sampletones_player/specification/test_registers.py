from functools import reduce
from operator import or_

import pytest

from sampletones_core.constants.general import MAX_TIMER
from sampletones_player.specification.registers import (
    CHANNEL_STATUS_BITS,
    CHANNELS_ENABLED,
    MAX_REGISTER_VALUE,
    MAX_TIMER_HIGH,
    TIMER_HIGH_SHIFT,
    divider,
)


class TestTheStatusRegister:
    """The value the driver enables the channels with is every channel's own status bit, the bits
    a trace reads each channel's enable from; both are the console's facts, so the case holds one
    against the other."""

    def test_enabling_the_channels_sets_each_channels_bit(self) -> None:
        assert reduce(or_, CHANNEL_STATUS_BITS.values()) == CHANNELS_ENABLED

    def test_each_channel_owns_one_bit_of_its_own(self) -> None:
        bits = list(CHANNEL_STATUS_BITS.values())
        assert all(bit and not bit & (bit - 1) for bit in bits)
        assert len(set(bits)) == len(bits)


class TestDivider:
    """A tone channel's two timer bytes carry one 11-bit divider."""

    @pytest.mark.parametrize("value", [0, 1, MAX_REGISTER_VALUE, MAX_REGISTER_VALUE + 1, MAX_TIMER])
    def test_the_bytes_a_divider_is_split_into_carry_it_back(self, value: int) -> None:
        high, low = value >> TIMER_HIGH_SHIFT, value & MAX_REGISTER_VALUE
        assert divider(high, low) == value

    def test_the_widest_bytes_carry_the_longest_divider(self) -> None:
        assert divider(MAX_TIMER_HIGH, MAX_REGISTER_VALUE) == MAX_TIMER
