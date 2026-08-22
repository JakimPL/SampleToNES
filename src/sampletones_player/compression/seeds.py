from typing import List, Tuple

from sampletones_core.exporters.maps import CHANNEL_TO_EXPORTER_MAP
from sampletones_core.exporters.slices import iterate_sample_slices
from sampletones_core.project.project import Project
from sampletones_core.timers.utils import get_timer_table
from sampletones_player.compression.dictionary.phrase import Phrase
from sampletones_player.compression.pitch import PitchTable
from sampletones_player.compression.planes.separate import channel_planes
from sampletones_player.registers.channel import channel_registers
from sampletones_player.specification.compression import MAX_PHRASE_LENGTH
from sampletones_shared.music import Tuning


def phrases_from_project(
    project: Project,
    tuning: Tuning,
) -> Tuple[Phrase, ...]:
    """The phrases a project's own instruments offer the dictionary.

    A song is built by playing sample slices at rows, so the shapes its planes repeat are the
    slices themselves: each one reaches the dictionary as the two planes it writes, at the pitch
    and level it was reconstructed at, and every row playing it names those entries at the shift
    the row asks for.

    Args:
        project: The project whose samples the song plays.
        tuning: Where concert pitch sits, which decides the timer each pitch sounds at.

    Returns:
        Tuple[Phrase, ...]: The phrases, in instrument-table order.
    """
    timer_table = get_timer_table(tuning)
    pitches = PitchTable.from_tuning(tuning)
    phrases: List[Phrase] = []
    for sample_slice in iterate_sample_slices(project):
        channel = sample_slice.channel
        played = {channel: CHANNEL_TO_EXPORTER_MAP[channel].from_features(sample_slice.features)}
        planes = channel_planes(
            channel,
            channel_registers(channel, played, timer_table),
            pitches,
        )
        phrases.extend(Phrase(body=plane[:MAX_PHRASE_LENGTH]) for plane in planes.ordered)

    return tuple(phrases)
