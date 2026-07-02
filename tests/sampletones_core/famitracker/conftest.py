from dataclasses import dataclass
from pathlib import Path
from typing import List, Mapping, Sequence

import numpy as np
import pytest

from sampletones_core.configs import Config
from sampletones_core.constants.enums import GeneratorName
from sampletones_core.instructions.implementation.noise import NoiseInstruction
from sampletones_core.instructions.implementation.pulse import PulseInstruction
from sampletones_core.instructions.implementation.triangle import TriangleInstruction
from sampletones_core.instructions.instruction import Instruction
from sampletones_core.project.instruments.instrument import Instrument
from sampletones_core.project.instruments.note_off import NoteOff
from sampletones_core.project.instruments.sample import Sample
from sampletones_core.project.patterns.channel import Channel
from sampletones_core.project.patterns.pattern import Pattern
from sampletones_core.project.patterns.row import Row
from sampletones_core.project.project import Project
from sampletones_core.project.settings import ProjectSettings
from sampletones_core.project.song import Song
from sampletones_core.reconstructions import Reconstruction
from sampletones_core.structures import IdentifiedCollection

RECONSTRUCTION_LENGTH = 8


def build_reconstruction(instructions: Mapping[GeneratorName, Sequence[Instruction]]) -> Reconstruction:
    approximations = {generator: np.zeros(RECONSTRUCTION_LENGTH, dtype=np.float32) for generator in instructions}
    return Reconstruction.create(
        approximation=np.zeros(RECONSTRUCTION_LENGTH, dtype=np.float32),
        approximations=approximations,
        instructions=instructions,
        config=Config(),
        coefficient=1.0,
        audio_filepath=Path("/dev/null"),
    )


def pulse_sample(name: str, pitch: int, *, loop: bool = False) -> Sample:
    instructions = [
        PulseInstruction(on=True, pitch=pitch, volume=15, duty_cycle=0),
        PulseInstruction(on=True, pitch=pitch, volume=8, duty_cycle=0),
    ]
    return Sample(name=name, reconstruction=build_reconstruction({GeneratorName.PULSE1: instructions}), loop=loop)


def noise_sample(name: str, period: int) -> Sample:
    instructions = [NoiseInstruction(on=True, period=period, volume=15, short=False)]
    return Sample(name=name, reconstruction=build_reconstruction({GeneratorName.NOISE: instructions}))


def dual_generator_sample(name: str, pulse_pitch: int, triangle_pitch: int) -> Sample:
    instructions: Mapping[GeneratorName, Sequence[Instruction]] = {
        GeneratorName.PULSE1: [PulseInstruction(on=True, pitch=pulse_pitch, volume=15, duty_cycle=0)],
        GeneratorName.TRIANGLE: [TriangleInstruction(on=True, pitch=triangle_pitch)],
    }
    return Sample(name=name, reconstruction=build_reconstruction(instructions))


@dataclass
class ProjectFixture:
    project: Project
    lead: Sample
    pad: Sample
    drum: Sample
    bell: Sample


@pytest.fixture
def project_fixture() -> ProjectFixture:
    lead = pulse_sample("lead", pitch=60)
    pad = pulse_sample("pad", pitch=48, loop=True)
    drum = noise_sample("drum", period=4)
    bell = dual_generator_sample("bell", pulse_pitch=72, triangle_pitch=36)

    samples: IdentifiedCollection[Sample] = IdentifiedCollection()
    for sample in (lead, pad, drum, bell):
        samples.append(sample)

    pulse_rows: List[Row] = [Row() for _ in range(8)]
    pulse_rows[0] = Row(
        command=Instrument(sample_id=lead.id, generator_name=GeneratorName.PULSE1), transpose=0, volume=10
    )
    pulse_rows[2] = Row(command=NoteOff())
    pulse_rows[4] = Row(volume=5)

    noise_rows: List[Row] = [Row() for _ in range(8)]
    noise_rows[0] = Row(
        command=Instrument(sample_id=drum.id, generator_name=GeneratorName.NOISE), transpose=0, volume=15
    )

    channels = {
        GeneratorName.PULSE1: Channel(generator=GeneratorName.PULSE1, patterns={0: Pattern(rows=pulse_rows)}),
        GeneratorName.PULSE2: Channel(generator=GeneratorName.PULSE2, patterns={}),
        GeneratorName.TRIANGLE: Channel(generator=GeneratorName.TRIANGLE, patterns={}),
        GeneratorName.NOISE: Channel(generator=GeneratorName.NOISE, patterns={0: Pattern(rows=noise_rows)}),
    }
    order = [
        {
            GeneratorName.PULSE1: 0,
            GeneratorName.PULSE2: None,
            GeneratorName.TRIANGLE: None,
            GeneratorName.NOISE: 0,
        },
        {
            GeneratorName.PULSE1: None,
            GeneratorName.PULSE2: None,
            GeneratorName.TRIANGLE: None,
            GeneratorName.NOISE: None,
        },
    ]
    song = Song(rows_per_pattern=8, order=order, channels=channels)

    project = Project.create(title="Demo", author="Tester", settings=ProjectSettings())
    project.info.comment = "a comment"
    project.samples = samples
    project.song = song

    return ProjectFixture(project=project, lead=lead, pad=pad, drum=drum, bell=bell)
