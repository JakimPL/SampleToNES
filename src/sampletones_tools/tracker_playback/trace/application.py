from typing import List, Tuple

from sampletones_core.constants.enums import ChannelName
from sampletones_core.constants.general import MAX_PERIOD, MAX_VOLUME
from sampletones_core.performance import song_instructions
from sampletones_core.project.project import Project
from sampletones_core.project.tuning import tuning_from_project
from sampletones_core.timers.utils import get_timer_table
from sampletones_core.timing import Groove, SongTiming
from sampletones_player.builder import streams_from_instructions
from sampletones_player.registers.base import ChannelRegisters
from sampletones_player.registers.hold import hold
from sampletones_player.registers.noise import NoiseRegisters
from sampletones_player.registers.pulse import PulseRegisters
from sampletones_player.registers.triangle import TriangleRegisters
from sampletones_player.specification.registers import (
    DUTY_CYCLE_SHIFT,
    NOISE_MODE_SHIFT,
    TRIANGLE_SILENT_RELOAD,
    TRIANGLE_SOUNDING_RELOAD,
)
from sampletones_tools.tracker_playback.trace.sound import (
    ABSENT_REGISTER,
    ChannelSound,
    SongTrace,
    TickPosition,
)


def application_trace(project: Project) -> SongTrace:
    """What the application plays of a project, tick by tick, as the registers the console writes.

    The song is walked once into the instructions each channel sounds, the same walk the sequencer
    and the NES player read, and those instructions become register values through the player's own
    encoding. Reading the registers back is what puts the application in the terms a tracker's trace
    is read in.

    Args:
        project: The project whose song is played.

    Returns:
        SongTrace: One pass through the song, the order played once.
    """
    timing = SongTiming.from_project(project)
    ticks = timing.frame_tick(project.song.order_length())
    streams = streams_from_instructions(
        song_instructions(project),
        get_timer_table(tuning_from_project(project)),
    )
    return SongTrace(
        positions=song_positions(
            timing.groove(),
            project.song.order_length(),
        ),
        channels={
            channel_name: tuple(register_sound(hold(stream, tick)) for tick in range(ticks))
            for channel_name, stream in zip(ChannelName.items(), streams.ordered, strict=True)
        },
    )


def song_positions(
    groove: Groove,
    frames: int,
) -> Tuple[TickPosition, ...]:
    """Where each tick of a song falls, every frame lasting one groove.

    Args:
        groove: The ticks each row of a pattern lasts.
        frames: The order frames the song plays.

    Returns:
        Tuple[TickPosition, ...]: One position per tick, in order.
    """
    positions: List[TickPosition] = []
    for frame in range(frames):
        for row, row_ticks in enumerate(groove.ticks):
            positions.extend(TickPosition(frame=frame, row=row) for _ in range(row_ticks))

    return tuple(positions)


def register_sound(registers: ChannelRegisters) -> ChannelSound:
    """What one channel's registers sound on a tick.

    Args:
        registers: The values the channel writes on the tick.

    Returns:
        ChannelSound: The channel's sound, read out of those values.

    Raises:
        TypeError: If the registers belong to no channel the console plays.
    """
    match registers:
        case PulseRegisters():
            return pulse_sound(registers)
        case TriangleRegisters():
            return triangle_sound(registers)
        case NoiseRegisters():
            return noise_sound(registers)

    raise TypeError(f"{type(registers).__name__} belongs to no channel the console plays")


def pulse_sound(registers: PulseRegisters) -> ChannelSound:
    """A pulse channel's sound: the level and the duty cycle ride the control byte, the timer the rest."""
    volume = registers.control & MAX_VOLUME
    return ChannelSound(
        audible=volume > 0,
        period=registers.divider,
        volume=volume,
        timbre=registers.control >> DUTY_CYCLE_SHIFT,
    )


def triangle_sound(registers: TriangleRegisters) -> ChannelSound:
    """The triangle's sound: the linear counter's reload says whether it sounds, the timer at what pitch."""
    reload_value = registers.linear_counter & TRIANGLE_SOUNDING_RELOAD
    return ChannelSound(
        audible=reload_value != TRIANGLE_SILENT_RELOAD,
        period=registers.divider,
        volume=ABSENT_REGISTER,
        timbre=ABSENT_REGISTER,
    )


def noise_sound(registers: NoiseRegisters) -> ChannelSound:
    """The noise channel's sound: the level rides the control byte, the period index and the mode the period byte."""
    volume = registers.control & MAX_VOLUME
    return ChannelSound(
        audible=volume > 0,
        period=registers.period & MAX_PERIOD,
        volume=volume,
        timbre=registers.period >> NOISE_MODE_SHIFT,
    )
