from typing import Dict, Final, Mapping, Optional, Sequence, Tuple

from sampletones_core.constants.enums import ChannelName
from sampletones_core.exporters.maps import CHANNEL_TO_EXPORTER_MAP
from sampletones_core.exports.request import InstrumentExport, SampleExport
from sampletones_core.instructions import InstructionUnion
from sampletones_core.performance import song_instructions
from sampletones_core.project.project import Project
from sampletones_core.reconstructions import Reconstruction
from sampletones_core.timers.utils import get_timer_table
from sampletones_player.clock.schedule import PlaySchedule
from sampletones_player.compression.dictionary.phrase import Phrase
from sampletones_player.compression.pitch import PitchTable
from sampletones_player.compression.seeds import phrases_from_project
from sampletones_player.registers.channel import channel_registers
from sampletones_player.registers.streams import ChannelStreams
from sampletones_player.song import Song
from sampletones_shared.music import Tuning

SONG_START: Final[int] = 0
NO_SEEDS: Final[Tuple[Phrase, ...]] = ()


def streams_from_instructions(
    instructions: Mapping[ChannelName, Sequence[InstructionUnion]],
    timer_table: Dict[int, int],
) -> ChannelStreams:
    """Encodes every channel's instructions into the register values its ticks write.

    The song covers all four channels, so a channel the mapping leaves out rests through it,
    the same as one whose stream describes no frame.

    Args:
        instructions: The stream each channel carries.
        timer_table: The timer register value each pitch sounds at.

    Returns:
        ChannelStreams: The four streams the driver plays.

    Raises:
        TypeError: If a channel's stream holds an instruction another channel sounds.
    """
    return ChannelStreams(
        pulse1=channel_registers(ChannelName.PULSE1, instructions, timer_table),
        pulse2=channel_registers(ChannelName.PULSE2, instructions, timer_table),
        triangle=channel_registers(ChannelName.TRIANGLE, instructions, timer_table),
        noise=channel_registers(ChannelName.NOISE, instructions, timer_table),
    )


def song_from_reconstruction(
    reconstruction: Reconstruction,
    loop_tick: Optional[int],
) -> Song:
    """Builds the song the console plays a reconstruction as.

    The reconstruction's own configuration carries both halves of the answer: the pitches it was
    built against become timers through the very table its generators render from, and the rate
    it was built at becomes the schedule the driver re-clocks the streams by.

    A reconstruction sounds each of its slices once, so the search fills the dictionary from what
    the streams themselves repeat.

    Args:
        reconstruction: The reconstruction to play.
        loop_tick: The tick the song returns to once it ends, or ``None`` where it stops there.

    Returns:
        Song: The streams, the clock and the loop point as the player holds them.

    Raises:
        TypeError: If a channel's stream holds an instruction another channel sounds.
        ValueError: If ``loop_tick`` lies outside the song's ticks.
    """
    tuning = reconstruction.config.tuning
    return Song.from_streams(
        streams=streams_from_instructions(
            reconstruction.instructions,
            get_timer_table(tuning),
        ),
        pitches=PitchTable.from_tuning(tuning),
        schedule=PlaySchedule.from_parameters(reconstruction.config.nes_frequency),
        loop_tick=loop_tick,
        seeds=NO_SEEDS,
    )


def instructions_from_instruments(
    instruments: Sequence[InstrumentExport],
) -> Dict[ChannelName, Sequence[InstructionUnion]]:
    """Reads every channel slice of an export request back as instructions.

    A request describes each slice as the envelopes an instrument carries, which is the form a
    tracker reads it in. The console sounds instructions instead, so each slice is walked back
    through the exporter belonging to the channel it was reconstructed for.

    Args:
        instruments: The slices to sound.

    Returns:
        Dict[ChannelName, Sequence[InstructionUnion]]: The stream each channel carries.

    Raises:
        ValueError: If two slices name the same channel, which the console sounds one of.
    """
    instructions: Dict[ChannelName, Sequence[InstructionUnion]] = {}
    for instrument in instruments:
        if instrument.channel in instructions:
            raise ValueError(f"Channel '{instrument.channel}' carries two slices, and the console sounds one")

        exporter = CHANNEL_TO_EXPORTER_MAP[instrument.channel]
        instructions[instrument.channel] = exporter.from_features(instrument.features)

    return instructions


def loop_tick_from_instruments(instruments: Sequence[InstrumentExport]) -> Optional[int]:
    """The tick a request's song returns to once it ends.

    A song repeats from its first tick where every slice it carries repeats, and ends at its
    last tick where any slice plays its envelopes once.

    Args:
        instruments: The slices the song carries.

    Returns:
        Optional[int]: The tick to return to, or ``None`` where the song stops at its end.
    """
    if instruments and all(instrument.loop for instrument in instruments):
        return SONG_START

    return None


def song_from_sample(request: SampleExport) -> Song:
    """Builds the song the console plays an export request as.

    Every slice sounds at once on the channel it was reconstructed for, and the request states
    both halves of what that takes: the tuning its pitches are measured from, and the rate its
    envelopes advance at, which the driver re-clocks to the rate the console calls it at.

    The request sounds each of its slices once, so the search fills the dictionary from what the
    streams themselves repeat.

    Args:
        request: The slices to play together.

    Returns:
        Song: The streams, the clock and the loop point as the player holds them.

    Raises:
        TypeError: If a channel's stream holds an instruction another channel sounds.
        ValueError: If two slices name the same channel.
    """
    return Song.from_streams(
        streams=streams_from_instructions(
            instructions_from_instruments(request.instruments),
            get_timer_table(request.tuning),
        ),
        pitches=PitchTable.from_tuning(request.tuning),
        schedule=PlaySchedule.from_parameters(request.nes_frequency),
        loop_tick=loop_tick_from_instruments(request.instruments),
        seeds=NO_SEEDS,
    )


def song_from_project(
    project: Project,
    tuning: Tuning,
    loop_tick: Optional[int],
) -> Song:
    """Builds the song the console plays a whole project as.

    The project's song is played out row by row into the instructions each channel sounds, so
    what reaches the console is the arrangement itself rather than one reconstruction: the same
    walk the sequencer sounds a song through, read as register values instead of audio. The
    project states the rate the driver re-clocks those ticks by.

    A row plays a sample the project already holds, so the samples themselves seed the dictionary
    and every row naming one reaches the stream as a token naming that entry.

    Args:
        project: The project whose song is played.
        tuning: Where concert pitch sits, which decides the timer each pitch sounds at.
        loop_tick: The tick the song returns to once it ends, or ``None`` where it stops there.

    Returns:
        Song: The streams, the clock and the loop point as the player holds them.

    Raises:
        TypeError: If a channel's stream holds an instruction another channel sounds.
        ValueError: If ``loop_tick`` lies outside the song's ticks.
    """
    return Song.from_streams(
        streams=streams_from_instructions(
            song_instructions(project),
            get_timer_table(tuning),
        ),
        pitches=PitchTable.from_tuning(tuning),
        schedule=PlaySchedule.from_parameters(project.settings.nes_frequency),
        loop_tick=loop_tick,
        seeds=phrases_from_project(project, tuning),
    )
