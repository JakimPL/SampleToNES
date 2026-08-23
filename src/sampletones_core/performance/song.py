from typing import Dict, List, Optional

from sampletones_core.constants.enums import ChannelName
from sampletones_core.exporters.maps import CHANNEL_TO_EXPORTER_MAP
from sampletones_core.instructions import InstructionUnion
from sampletones_core.performance.progress import (
    WalkReporter,
    announce,
)
from sampletones_core.performance.rows import apply_row, resolve_row
from sampletones_core.performance.state import ChannelPerformance
from sampletones_core.performance.ticks import sound_tick
from sampletones_core.performance.voice import VoiceReading
from sampletones_core.project.project import Project
from sampletones_core.project.song_position import SongPosition
from sampletones_core.project.voices.voice import VoiceUnion
from sampletones_core.timing.song import SongTiming
from sampletones_shared.utils.progress import silent_reporter


def song_instructions(
    project: Project,
    report: WalkReporter = silent_reporter,
) -> Dict[ChannelName, List[InstructionUnion]]:
    """Plays a whole song out as the instructions each channel sounds, one per engine tick.

    The order is walked frame by frame and row by row, each row lasting the ticks the project's
    groove gives its position within the pattern. Every channel answers for each of those ticks,
    so the four streams share one length and a tick's index into them is the same moment of the
    song — which is what an engine consuming one instruction per tick plays from.

    The groove states the ticks the whole order lasts before a row is played, so a walk of a song
    of minutes says how far along it is and answers a caller who no longer wants it.

    Args:
        project: The project whose song is played.
        report: Hears how far the walk has sounded, and answers whether it goes on.

    Returns:
        Dict[ChannelName, List[InstructionUnion]]: Each channel's stream, tick by tick.

    Raises:
        OperationCancelled: If ``report`` withdraws the walk.
    """
    song = project.song
    groove = SongTiming.from_project(project).groove()
    total = groove.total_ticks * song.order_length()
    performances = {channel_name: ChannelPerformance() for channel_name in ChannelName.items()}
    streams: Dict[ChannelName, List[InstructionUnion]] = {channel_name: [] for channel_name in ChannelName.items()}

    position = SongPosition()
    walked = 0
    while position.order_position < song.order_length():
        ticks = groove.ticks[position.row_index]
        for channel_name in ChannelName.items():
            performance = performances[channel_name]
            row = resolve_row(song, position, channel_name)
            if row is not None:
                apply_row(performance, row)

            streams[channel_name].extend(
                _channel_ticks(
                    project.voice(performance.voice_id) if performance.voice_id is not None else None,
                    channel_name,
                    performance,
                    ticks,
                )
            )

        walked += ticks
        announce(report, walked, total)
        position.advance(song.rows_per_pattern, song.order_length())

    return streams


def _channel_ticks(
    voice: Optional[VoiceUnion],
    channel_name: ChannelName,
    performance: ChannelPerformance,
    ticks: int,
) -> List[InstructionUnion]:
    """One channel's instructions across a single row.

    A channel with nothing to sound rests for the whole row and keeps the tick it had reached,
    so a voice removed from the project leaves the rows that named it silent while the rows
    around them play on.

    Args:
        voice: The voice the channel is sounding, or ``None`` while it rests.
        channel_name: The channel being sounded.
        performance: What the channel carries; its tick index moves on per sounded tick.
        ticks: The engine ticks the row lasts.

    Returns:
        List[InstructionUnion]: One instruction per tick of the row.
    """
    resting: InstructionUnion = CHANNEL_TO_EXPORTER_MAP[channel_name].get_instruction_type().null_instruction()
    reading = VoiceReading.read(voice, channel_name) if voice is not None else None
    if reading is None:
        return [resting] * ticks

    sounded: List[InstructionUnion] = []
    for _ in range(ticks):
        instruction = sound_tick(performance, reading)
        sounded.append(resting if instruction is None else instruction)

    return sounded
