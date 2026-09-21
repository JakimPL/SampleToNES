from typing import List, Tuple

from sampletones_core.constants.enums import TONE_CHANNELS
from sampletones_core.exporters.maps import CHANNEL_TO_EXPORTER_MAP
from sampletones_core.exporters.slices import iterate_voice_slices
from sampletones_core.project.project import Project
from sampletones_core.timers.utils import get_timer_table
from sampletones_player.compression.pitch import PitchTable
from sampletones_player.compression.planes.separate import channel_planes
from sampletones_player.registers.channel import channel_registers
from sampletones_shared.music import Tuning
from sampletones_tools.codec.study.corpus.notes import channel_notes
from sampletones_tools.codec.study.corpus.song import StudySlice


def project_slices(
    project: Project,
    tuning: Tuning,
) -> Tuple[StudySlice, ...]:
    """Every channel of every voice a project holds, in the order its instruments seed a song.

    This is the reading ``phrases_from_project`` seeds the production dictionary from, kept whole
    so a plane layout can separate each slice its own way.

    Args:
        project: The project whose voices are read.
        tuning: Where concert pitch sits, which decides the timer each pitch sounds at.

    Returns:
        Tuple[StudySlice, ...]: The slices, in instrument-table order.
    """
    timer_table = get_timer_table(tuning)
    pitches = PitchTable.from_tuning(tuning)
    slices: List[StudySlice] = []
    for voice_slice in iterate_voice_slices(project):
        channel = voice_slice.channel
        instructions = CHANNEL_TO_EXPORTER_MAP[channel].from_features(voice_slice.features)
        registers = channel_registers(channel, {channel: instructions}, timer_table)
        slices.append(
            StudySlice(
                channel=channel,
                planes=channel_planes(channel, registers, pitches),
                notes=channel_notes(channel, instructions) if channel in TONE_CHANNELS else b"",
            )
        )

    return tuple(slices)
