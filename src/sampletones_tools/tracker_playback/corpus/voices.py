from pathlib import Path
from typing import Dict, Final, List, Sequence, Tuple

from sampletones_core.constants.enums import ChannelName
from sampletones_core.exporters.maps import CHANNEL_TO_EXPORTER_MAP
from sampletones_core.instructions import InstructionUnion
from sampletones_core.project.voices.instrument import Instrument
from sampletones_core.project.voices.sample import Sample
from sampletones_core.project.voices.voice import VoiceUnion
from sampletones_tools.corpus.written import written_reconstruction
from sampletones_tools.tracker_playback.corpus.spec import (
    FrameRun,
    InstrumentSpec,
    SampleSpec,
    VoiceSpec,
)

WRITTEN_COEFFICIENT: Final[float] = 1.0
WRITTEN_SCALE: Final[float] = 1.0
NO_RECORDINGS: Final[Tuple[Path, ...]] = ()


def channel_frames(
    channel: ChannelName,
    runs: Sequence[FrameRun],
) -> List[InstructionUnion]:
    """The frames one channel of a sample plays, each run read as the instruction that channel takes.

    Args:
        channel: The channel the frames play on.
        runs: The runs of alike frames, in order.

    Returns:
        List[InstructionUnion]: One instruction per frame.

    Raises:
        ValidationError: If a run's frame is no instruction the channel takes.
    """
    instruction_type = CHANNEL_TO_EXPORTER_MAP[channel].get_instruction_type()
    frames: List[InstructionUnion] = []
    for run in runs:
        frame = instruction_type.model_validate(run.frame)
        frames.extend(frame for _ in range(run.count))

    return frames


def build_voice(
    name: str,
    spec: VoiceSpec,
) -> VoiceUnion:
    """The voice a spec describes: a sample playing its written frames, or a hand-written instrument.

    Args:
        name: The voice's name.
        spec: What the voice plays.

    Returns:
        VoiceUnion: The voice.
    """
    match spec:
        case SampleSpec():
            instructions: Dict[ChannelName, List[InstructionUnion]] = {
                channel: channel_frames(channel, runs) for channel, runs in spec.channels.items()
            }
            return Sample(
                name=name,
                reconstruction=written_reconstruction(
                    instructions,
                    coefficient=WRITTEN_COEFFICIENT,
                    scale=WRITTEN_SCALE,
                    audio_filepath=NO_RECORDINGS,
                ),
            )
        case InstrumentSpec():
            return Instrument(
                name=name,
                initial_pitch=spec.initial_pitch,
                initial_period=spec.initial_period,
                envelopes=spec.envelopes,
            )
