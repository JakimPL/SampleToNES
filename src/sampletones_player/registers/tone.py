from abc import ABC

from pydantic import Field

from sampletones_player.registers.base import ChannelRegisters
from sampletones_player.specification.registers import (
    MAX_REGISTER_VALUE,
    MAX_TIMER_HIGH,
    TIMER_HIGH_SHIFT,
)
from sampletones_shared.constants.music import LIMIT_MAX_PITCH, LIMIT_MIN_PITCH


class ToneRegisters(ChannelRegisters, ABC):
    """The timer a tone channel writes for one tick, beside the pitch its divider is counted from.

    The anchor never reaches a register. It is what the channel's value plane names, and the bend
    plane holds the steps from that pitch's own divider to the one written, which the driver adds
    back.

    Attributes:
        timer_low: The timer's low byte.
        timer_high: The timer's high bits.
        anchor: The pitch the divider is counted from.
    """

    timer_low: int = Field(..., ge=0, le=MAX_REGISTER_VALUE)
    timer_high: int = Field(..., ge=0, le=MAX_TIMER_HIGH)
    anchor: int = Field(..., ge=LIMIT_MIN_PITCH, le=LIMIT_MAX_PITCH)

    @property
    def divider(self) -> int:
        """The divider the two halves of the timer carry together."""
        return (self.timer_high << TIMER_HIGH_SHIFT) | self.timer_low
