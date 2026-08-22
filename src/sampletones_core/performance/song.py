from typing import Dict, List, Optional

from sampletones_core.constants.enums import ChannelName
from sampletones_core.exporters.maps import CHANNEL_TO_EXPORTER_MAP
from sampletones_core.instructions import InstructionUnion
from sampletones_core.performance.rows import apply_row, resolve_row
from sampletones_core.performance.state import ChannelPerformance
from sampletones_core.performance.ticks import sound_tick
from sampletones_core.performance.voice import SampleVoice
from sampletones_core.project.instruments.sample import Sample
from sampletones_core.project.project import Project
from sampletones_core.project.song_position import SongPosition
from sampletones_core.timing.song import SongTiming


def song_instructions(project: Project) -> Dict[ChannelName, List[InstructionUnion]]:
    """Plays a whole song out as the instructions each channel sounds, one per engine tick.

    The order is walked frame by frame and row by row, each row lasting the ticks the project's
    groove gives its position within the pattern. Every channel answers for each of those ticks,
    so the four streams share one length and a tick's index into them is the same moment of the
    song — which is what an engine consuming one instruction per tick plays from.

    Args:
        project: The project whose song is played.

    Returns:
        Dict[ChannelName, List[InstructionUnion]]: Each channel's stream, tick by tick.
    """
    song = project.song
    groove = SongTiming.from_project(project).groove()
    performances = {channel_name: ChannelPerformance() for channel_name in ChannelName.items()}
    streams: Dict[ChannelName, List[InstructionUnion]] = {channel_name: [] for channel_name in ChannelName.items()}

    position = SongPosition()
    while position.order_position < song.order_length():
        ticks = groove.ticks[position.row_index]
        for channel_name in ChannelName.items():
            performance = performances[channel_name]
            row = resolve_row(song, position, channel_name)
            if row is not None:
                apply_row(performance, row)

            streams[channel_name].extend(
                _channel_ticks(
                    project.sample(performance.sample_id) if performance.sample_id is not None else None,
                    channel_name,
                    performance,
                    ticks,
                )
            )

        position.advance(song.rows_per_pattern, song.order_length())

    return streams


def _channel_ticks(
    sample: Optional[Sample],
    channel_name: ChannelName,
    performance: ChannelPerformance,
    ticks: int,
) -> List[InstructionUnion]:
    """One channel's instructions across a single row.

    A channel with nothing to sound rests for the whole row and keeps the tick it had reached,
    so a sample removed from the project leaves the rows that named it silent while the rows
    around them play on.

    Args:
        sample: The sample the channel is sounding, or ``None`` while it rests.
        channel_name: The channel being sounded.
        performance: What the channel carries; its tick index moves on per sounded tick.
        ticks: The engine ticks the row lasts.

    Returns:
        List[InstructionUnion]: One instruction per tick of the row.
    """
    resting: InstructionUnion = CHANNEL_TO_EXPORTER_MAP[channel_name].get_instruction_type().null_instruction()
    if sample is None:
        return [resting] * ticks

    instructions = sample.reconstruction.instructions[channel_name]
    if not instructions:
        return [resting] * ticks

    voice = SampleVoice.read(sample.reconstruction, channel_name)
    sounded: List[InstructionUnion] = []
    for _ in range(ticks):
        instruction = sound_tick(
            performance,
            instructions,
            loop=sample.loop,
            voice=voice,
        )
        sounded.append(resting if instruction is None else instruction)

    return sounded
