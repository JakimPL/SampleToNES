from typing import Dict, Final, NamedTuple, Sequence, Tuple

from sampletones_core.constants.enums import ChannelName
from sampletones_core.constants.general import MAX_PERIOD, MAX_VOLUME, SILENT_VOLUME
from sampletones_player.specification.registers import (
    APU_STATUS,
    CONSTANT_VOLUME,
    DUTY_CYCLE_SHIFT,
    MAX_TIMER_HIGH,
    NOISE_CONTROL,
    NOISE_MODE_SHIFT,
    NOISE_PERIOD,
    PULSE1_CONTROL,
    PULSE1_TIMER_HIGH,
    PULSE1_TIMER_LOW,
    PULSE2_CONTROL,
    PULSE2_TIMER_HIGH,
    PULSE2_TIMER_LOW,
    SUSTAINED_LEVEL,
    TIMER_HIGH_SHIFT,
    TRIANGLE_COUNTER_CONTROL,
    TRIANGLE_LINEAR_COUNTER,
    TRIANGLE_TIMER_HIGH,
    TRIANGLE_TIMER_LOW,
)
from sampletones_tools.tracker_playback.trace.registers import ChipRegisters
from sampletones_tools.tracker_playback.trace.sound import (
    ABSENT_REGISTER,
    ChannelSound,
    SongTrace,
    TickPosition,
)

CHANNEL_STATUS_BITS: Final[Dict[ChannelName, int]] = {
    ChannelName.PULSE1: 0x01,
    ChannelName.PULSE2: 0x02,
    ChannelName.TRIANGLE: 0x04,
    ChannelName.NOISE: 0x08,
}
DMC_STATUS_BIT: Final[int] = 0x10
LINEAR_COUNTER_RELOAD: Final[int] = 0x7F


class ToneAddresses(NamedTuple):
    """The registers a pulse or triangle channel keeps its control byte and its timer in.

    Attributes:
        control: The byte carrying the level and the duty cycle on a pulse channel, and the linear
            counter on the triangle.
        timer_low: The timer's low byte.
        timer_high: The byte carrying the timer's top three bits under the length index.
    """

    control: int
    timer_low: int
    timer_high: int


TONE_ADDRESSES: Final[Dict[ChannelName, ToneAddresses]] = {
    ChannelName.PULSE1: ToneAddresses(
        control=PULSE1_CONTROL,
        timer_low=PULSE1_TIMER_LOW,
        timer_high=PULSE1_TIMER_HIGH,
    ),
    ChannelName.PULSE2: ToneAddresses(
        control=PULSE2_CONTROL,
        timer_low=PULSE2_TIMER_LOW,
        timer_high=PULSE2_TIMER_HIGH,
    ),
    ChannelName.TRIANGLE: ToneAddresses(
        control=TRIANGLE_LINEAR_COUNTER,
        timer_low=TRIANGLE_TIMER_LOW,
        timer_high=TRIANGLE_TIMER_HIGH,
    ),
}


def song_trace(
    positions: Tuple[TickPosition, ...],
    registers: Sequence[ChipRegisters],
) -> SongTrace:
    """What every channel plays on every tick of a song, read out of the registers the chip holds on each.

    Args:
        positions: Where each tick falls.
        registers: The chip's registers on each tick, one per position.

    Returns:
        SongTrace: Each channel's sound on every tick.

    Raises:
        ValueError: If the registers cover a different number of ticks than the positions.
    """
    if len(registers) != len(positions):
        raise ValueError(f"{len(positions)} ticks have {len(registers)} register states")

    return SongTrace(
        positions=positions,
        channels={
            channel: tuple(channel_sound(channel, tick_registers) for tick_registers in registers)
            for channel in ChannelName.items()
        },
    )


def channel_sound(
    channel: ChannelName,
    registers: ChipRegisters,
) -> ChannelSound:
    """What the chip plays of one channel from the registers it holds.

    Args:
        channel: The channel read.
        registers: The chip's registers.

    Returns:
        ChannelSound: The channel's sound.
    """
    match channel:
        case ChannelName.PULSE1 | ChannelName.PULSE2:
            return pulse_sound(channel, registers)
        case ChannelName.TRIANGLE:
            return triangle_sound(registers)
        case ChannelName.NOISE:
            return noise_sound(registers)


def pulse_sound(
    channel: ChannelName,
    registers: ChipRegisters,
) -> ChannelSound:
    """A pulse channel's sound: the duty cycle and the level ride its control byte, the timer its two timer bytes.

    Args:
        channel: The pulse channel read.
        registers: The chip's registers.

    Returns:
        ChannelSound: The channel's sound.
    """
    addresses = TONE_ADDRESSES[channel]
    control = registers.value(addresses.control)
    return ChannelSound(
        audible=is_enabled(channel, registers) and level_sounds(control),
        period=timer(addresses, registers),
        volume=control & MAX_VOLUME,
        held=level_held(control),
        timbre=control >> DUTY_CYCLE_SHIFT,
    )


def triangle_sound(registers: ChipRegisters) -> ChannelSound:
    """The triangle's sound: the linear counter's reload says whether it sounds, the timer at what pitch.

    A reload of zero leaves the counter at zero, which stops the waveform. The control flag reloads
    the counter every frame, holding the note for as long as the registers stay.

    Args:
        registers: The chip's registers.

    Returns:
        ChannelSound: The channel's sound.
    """
    addresses = TONE_ADDRESSES[ChannelName.TRIANGLE]
    control = registers.value(addresses.control)
    return ChannelSound(
        audible=is_enabled(ChannelName.TRIANGLE, registers) and (control & LINEAR_COUNTER_RELOAD) > 0,
        period=timer(addresses, registers),
        volume=ABSENT_REGISTER,
        held=bool(control & TRIANGLE_COUNTER_CONTROL),
        timbre=ABSENT_REGISTER,
    )


def noise_sound(registers: ChipRegisters) -> ChannelSound:
    """The noise channel's sound: the level rides its control byte, the period index and the mode its period byte.

    Args:
        registers: The chip's registers.

    Returns:
        ChannelSound: The channel's sound.
    """
    control = registers.value(NOISE_CONTROL)
    period = registers.value(NOISE_PERIOD)
    return ChannelSound(
        audible=is_enabled(ChannelName.NOISE, registers) and level_sounds(control),
        period=period & MAX_PERIOD,
        volume=control & MAX_VOLUME,
        held=level_held(control),
        timbre=period >> NOISE_MODE_SHIFT,
    )


def is_enabled(
    channel: ChannelName,
    registers: ChipRegisters,
) -> bool:
    """Whether the status register enables a channel, the first thing a channel needs to sound."""
    return bool(registers.value(APU_STATUS) & CHANNEL_STATUS_BITS[channel])


def timer(
    addresses: ToneAddresses,
    registers: ChipRegisters,
) -> int:
    """The 11-bit timer a pulse or triangle channel's two timer bytes carry together."""
    high = registers.value(addresses.timer_high) & MAX_TIMER_HIGH
    return (high << TIMER_HIGH_SHIFT) | registers.value(addresses.timer_low)


def level_sounds(control: int) -> bool:
    """Whether a pulse or noise control byte sounds: a constant level above zero, or the envelope, opening at full."""
    return not (control & CONSTANT_VOLUME) or (control & MAX_VOLUME) > SILENT_VOLUME


def level_held(control: int) -> bool:
    """Whether a pulse or noise control byte holds its level: a constant volume under a halted length counter."""
    return (control & SUSTAINED_LEVEL) == SUSTAINED_LEVEL
