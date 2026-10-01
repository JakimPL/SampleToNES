from typing import List, Tuple

from sampletones_core.performance import song_instructions
from sampletones_core.project.project import Project
from sampletones_core.project.tuning import tuning_from_project
from sampletones_core.timers.utils import get_timer_table
from sampletones_core.timing import SONG_TICK_BOUNDS, SongTiming
from sampletones_player.builder import streams_from_instructions
from sampletones_player.registers.streams import ChannelStreams
from sampletones_tools.player.trace.trace import channel_writes, setup_writes
from sampletones_tools.tracker_playback.trace.decode import song_trace
from sampletones_tools.tracker_playback.trace.registers import ChipRegisters
from sampletones_tools.tracker_playback.trace.sound import SongTrace, TickPosition


def application_trace(project: Project) -> SongTrace:
    """What the application plays of a project, tick by tick, read out of the registers the console holds.

    The song is walked once into the instructions each channel sounds, the same walk the sequencer
    and the NES player read, and those instructions become register values through the player's own
    encoding. The registers the driver writes are then read the way a tracker's are, so both sides
    of a comparison come out of the chip's registers by one rule.

    Args:
        project: The project whose song is played.

    Returns:
        SongTrace: One pass through the song, the order played once.
    """
    timing = SongTiming.from_project(project, bounds=SONG_TICK_BOUNDS)
    streams = streams_from_instructions(
        song_instructions(project),
        get_timer_table(tuning_from_project(project)),
    )
    return song_trace(
        song_positions(
            timing,
            project.song.order_length(),
        ),
        driver_registers(
            streams,
            timing.frame_tick(project.song.order_length()),
        ),
    )


def driver_registers(
    streams: ChannelStreams,
    ticks: int,
) -> Tuple[ChipRegisters, ...]:
    """The console's registers on every tick of a song as the NES player's driver leaves them.

    The driver's init routine sets the console up, and every tick writes each channel's registers
    over what the tick before left. A channel past the end of its stream holds its final values.

    Args:
        streams: The register values each channel writes on each tick.
        ticks: The ticks the song lasts.

    Returns:
        Tuple[ChipRegisters, ...]: The registers on each tick, one per tick.
    """
    registers = ChipRegisters.power_up().written(setup_writes())
    per_tick: List[ChipRegisters] = []
    for tick in range(ticks):
        registers = registers.written(channel_writes(streams.at(tick)))
        per_tick.append(registers)

    return tuple(per_tick)


def song_positions(
    timing: SongTiming,
    frames: int,
) -> Tuple[TickPosition, ...]:
    """Where each tick of a song falls, every frame lasting the groove its place in the song gives it.

    Args:
        timing: How many ticks every row of the song lasts.
        frames: The order frames the song plays.

    Returns:
        Tuple[TickPosition, ...]: One position per tick, in order.
    """
    positions: List[TickPosition] = []
    for frame in range(frames):
        for row, row_ticks in enumerate(timing.groove(frame).ticks):
            positions.extend(TickPosition(frame=frame, row=row) for _ in range(row_ticks))

    return tuple(positions)
