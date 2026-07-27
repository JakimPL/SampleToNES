from pathlib import Path
from typing import FrozenSet

import numpy as np
import pytest

from sampletones_application.logic.project.controller import ProjectController
from sampletones_application.logic.project.manager import ProjectManager
from sampletones_application.logic.sequencer.channels import ALL_CHANNELS
from sampletones_application.logic.sequencer.playback.synthesizer import RowSynthesizer
from sampletones_core.configs import Config
from sampletones_core.constants.enums import GeneratorName
from sampletones_core.instructions import (
    NoiseInstruction,
    PulseInstruction,
    TriangleInstruction,
)
from sampletones_core.project.instruments.instrument import Instrument
from sampletones_core.project.instruments.note_off import NoteOff
from sampletones_core.project.instruments.sample import Sample
from sampletones_core.reconstructions import Reconstruction


def make_controller() -> ProjectController:
    return ProjectController(ProjectManager())


def all_channels() -> FrozenSet[GeneratorName]:
    """The fully audible mask a synthesiser renders under unless a test moves it."""
    return ALL_CHANNELS


def make_pulse_reconstruction(
    *,
    pitch: int = 60,
    volume: int = 15,
    count: int = 1,
) -> Reconstruction:
    """Single-generator reconstruction with ``count`` identical PulseInstructions."""
    instructions = [PulseInstruction(on=True, pitch=pitch, volume=volume, duty_cycle=0)] * count
    return Reconstruction.create(
        approximation=np.zeros(64, dtype=np.float32),
        approximations={GeneratorName.PULSE1: np.zeros(64, dtype=np.float32)},
        instructions={GeneratorName.PULSE1: instructions},
        config=Config(),
        coefficient=1.0,
        audio_filepath=Path("/dev/null"),
    )


def make_triangle_reconstruction(
    *,
    pitch: int = 60,
    count: int = 1,
) -> Reconstruction:
    instructions = [TriangleInstruction(on=True, pitch=pitch)] * count
    return Reconstruction.create(
        approximation=np.zeros(64, dtype=np.float32),
        approximations={GeneratorName.TRIANGLE: np.zeros(64, dtype=np.float32)},
        instructions={GeneratorName.TRIANGLE: instructions},
        config=Config(),
        coefficient=1.0,
        audio_filepath=Path("/dev/null"),
    )


def make_noise_reconstruction(
    *,
    period: int = 3,
    volume: int = 15,
    count: int = 1,
) -> Reconstruction:
    instructions = [NoiseInstruction(on=True, period=period, volume=volume, short=False)] * count
    return Reconstruction.create(
        approximation=np.zeros(64, dtype=np.float32),
        approximations={GeneratorName.NOISE: np.zeros(64, dtype=np.float32)},
        instructions={GeneratorName.NOISE: instructions},
        config=Config(),
        coefficient=1.0,
        audio_filepath=Path("/dev/null"),
    )


def add_sample(
    controller: ProjectController,
    reconstruction: Reconstruction,
    *,
    loop: bool = False,
    name: str = "test",
) -> Sample:
    sample = controller.add_sample(reconstruction, name)
    if loop:
        controller.set_sample_loop(sample.id, loop=True)
    return sample


def place_row(
    controller: ProjectController,
    *,
    generator: GeneratorName,
    row_index: int = 0,
    sample_id: str,
    transpose: int | None = None,
    volume: int | None = None,
) -> None:
    pattern_index = controller.project.song.order[0][generator]
    controller.set_row(
        generator,
        pattern_index,
        row_index,
        command=Instrument(sample_id=sample_id, generator_name=generator),
        transpose=transpose,
        volume=volume,
    )


def place_note_off(
    controller: ProjectController,
    *,
    generator: GeneratorName,
    row_index: int,
) -> None:
    """Place an explicit note-off command on a channel row."""
    pattern_index = controller.project.song.order[0][generator]
    controller.set_row(generator, pattern_index, row_index, command=NoteOff())


def place_modifier_row(
    controller: ProjectController,
    *,
    generator: GeneratorName,
    row_index: int,
    transpose: int | None = None,
    volume: int | None = None,
) -> None:
    """Place a row with only modifiers (no instrument)."""
    pattern_index = controller.project.song.order[0][generator]
    controller.update_row(
        generator,
        pattern_index,
        row_index,
        transpose=transpose,
        volume=volume,
    )


@pytest.fixture
def config() -> Config:
    return Config()


@pytest.fixture
def controller() -> ProjectController:
    return make_controller()


@pytest.fixture
def synthesizer(controller: ProjectController, config: Config) -> RowSynthesizer:
    return RowSynthesizer(controller, config, active_channels=all_channels)
