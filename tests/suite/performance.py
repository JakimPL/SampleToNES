from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import numpy as np

from sampletones_core.configs import Config
from sampletones_core.constants.enums import ChannelName, FeatureKey
from sampletones_core.instructions import (
    InstructionUnion,
    NoiseInstruction,
    PulseInstruction,
    TriangleInstruction,
)
from sampletones_core.project.instruments.instrument import Instrument
from sampletones_core.project.instruments.sample import Sample
from sampletones_core.project.patterns.row import Row
from sampletones_core.project.project import Project
from sampletones_core.project.settings import ProjectSettings
from sampletones_core.reconstructions import Reconstruction
from tests.suite.stems import single_entry_stems_data

APPROXIMATION_LENGTH: int = 64


def _reconstruction(
    channel_name: ChannelName,
    instructions: List[InstructionUnion],
) -> Reconstruction:
    approximation = np.zeros(APPROXIMATION_LENGTH, dtype=np.float32)
    channel_instructions: Dict[ChannelName, List[InstructionUnion]] = {channel_name: instructions}
    return Reconstruction.create(
        approximation=approximation,
        approximations={channel_name: approximation},
        instructions=channel_instructions,
        config=Config(),
        coefficient=1.0,
        audio_filepath=(Path("/dev/null"),),
        stems_data=single_entry_stems_data(
            list(Config().generation.channels),
            channel_instructions,
        ),
    )


def make_pulse_reconstruction(
    *,
    pitch: int = 60,
    volume: int = 15,
    count: int = 1,
    held_features: Iterable[FeatureKey] = (),
) -> Reconstruction:
    """Single-channel reconstruction with ``count`` identical PulseInstructions.

    ``held_features`` names the dimensions the instrument leaves to the channel, which is what
    an envelope cleared in the instruments panel produces.
    """
    instructions: List[InstructionUnion] = [PulseInstruction(on=True, pitch=pitch, volume=volume, duty_cycle=0)] * count
    reconstruction = _reconstruction(ChannelName.PULSE1, instructions)
    if held_features:
        reconstruction.update_channel_data(
            ChannelName.PULSE1,
            list(instructions),
            np.zeros(APPROXIMATION_LENGTH, dtype=np.float32),
            reconstruction.initial_pitches[ChannelName.PULSE1],
            held_features,
        )

    return reconstruction


def make_triangle_reconstruction(
    *,
    pitch: int = 60,
    count: int = 1,
) -> Reconstruction:
    """Single-channel reconstruction with ``count`` identical TriangleInstructions."""
    instructions: List[InstructionUnion] = [TriangleInstruction(on=True, pitch=pitch)] * count
    return _reconstruction(ChannelName.TRIANGLE, instructions)


def make_noise_reconstruction(
    *,
    period: int = 3,
    volume: int = 15,
    count: int = 1,
) -> Reconstruction:
    """Single-channel reconstruction with ``count`` identical NoiseInstructions."""
    instructions: List[InstructionUnion] = [
        NoiseInstruction(on=True, period=period, volume=volume, short=False)
    ] * count
    return _reconstruction(ChannelName.NOISE, instructions)


def project_with_sample(
    reconstruction: Reconstruction,
    *,
    rows_per_pattern: int,
    settings: Optional[ProjectSettings] = None,
    loop: bool = False,
    name: str = "test",
) -> Tuple[Project, Sample]:
    """A one-sample project, built through the core models a document is made of.

    Answering with the sample beside the project is what lets a case place it on a row without
    reaching back into the collection for an id it already knows.
    """
    project = Project.create(rows_per_pattern=rows_per_pattern, settings=settings)
    sample = Sample(name=name, reconstruction=reconstruction, loop=loop)
    project.samples.append(sample)
    return project, sample


def place_instrument(
    project: Project,
    *,
    channel_name: ChannelName,
    row_index: int,
    sample: Sample,
    transpose: Optional[int] = None,
    volume: Optional[int] = None,
    pattern_index: int = 0,
) -> None:
    """Writes a note column naming ``sample`` onto one row of one channel's pattern."""
    pattern = project.song.channels[channel_name].ensure_pattern(
        pattern_index,
        project.song.rows_per_pattern,
    )
    pattern.rows[row_index] = Row(
        command=Instrument(sample_id=sample.id, channel_name=channel_name),
        transpose=transpose,
        volume=volume,
    )
