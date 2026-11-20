from pathlib import Path
from typing import Any, Dict, Final, FrozenSet, List

import numpy as np
import pytest

from sampletones_core.audio import write_wave
from sampletones_core.configs import Config
from sampletones_core.constants.enums import AssignmentMethod, ChannelName
from sampletones_core.fft import Window
from sampletones_core.fft.features import get_feature_extractor
from sampletones_core.generators import get_generators_by_channels
from sampletones_core.generators.render import render_instructions
from sampletones_core.instructions import InstructionUnion, NoiseInstruction, PulseInstruction, TriangleInstruction
from sampletones_core.library import InstructionLibrary, InstructionLibraryData, InstructionLibraryFragment
from sampletones_core.reconstructions import Reconstruction, Reconstructor
from sampletones_core.reconstructions.reconstructor.stems.configs.config import StemsConfig
from sampletones_core.reconstructions.reconstructor.stems.configs.settings import StemSettings

EVERY_CHANNEL: Final[List[ChannelName]] = ChannelName.items()
PULSE_PITCHES: Final[FrozenSet[int]] = frozenset({48, 55, 60, 64, 67, 72})
PULSE_VOLUMES: Final[FrozenSet[int]] = frozenset({4, 8, 12, 15})
DUTY_CYCLES: Final[FrozenSet[int]] = frozenset({1, 2})
TRIANGLE_PITCHES: Final[FrozenSet[int]] = frozenset({48, 55, 60, 64})
NOISE_PERIODS: Final[FrozenSet[int]] = frozenset({4, 8})
FRAMES: Final[int] = 24
EDGE_FRAMES: Final[int] = 3
RIGHT_SHARE: Final[float] = 0.9
CHORD: Final[Dict[ChannelName, InstructionUnion]] = {
    ChannelName.PULSE1: PulseInstruction(on=True, pitch=64, volume=12, duty_cycle=2),
    ChannelName.PULSE2: PulseInstruction(on=True, pitch=67, volume=8, duty_cycle=1),
    ChannelName.TRIANGLE: TriangleInstruction(on=True, pitch=48),
}


def _kept(instruction: InstructionUnion) -> bool:
    if not instruction.on:
        return True

    match instruction:
        case PulseInstruction():
            return (
                instruction.pitch in PULSE_PITCHES
                and instruction.volume in PULSE_VOLUMES
                and instruction.duty_cycle in DUTY_CYCLES
            )
        case TriangleInstruction():
            return instruction.pitch in TRIANGLE_PITCHES
        case NoiseInstruction():
            return instruction.period in NOISE_PERIODS and instruction.volume in PULSE_VOLUMES and not instruction.short
        case _:
            return False


def _library(config: Config) -> InstructionLibrary:
    """A few notes of every kind around the chord, at a spread of volumes."""
    window = Window.from_config(config)
    extractor = get_feature_extractor(config, window)
    data: Dict[InstructionUnion, InstructionLibraryFragment[Any]] = {}
    for generator in get_generators_by_channels(
        config, [ChannelName.PULSE1, ChannelName.TRIANGLE, ChannelName.NOISE]
    ).values():
        for instruction in generator.get_possible_instructions():
            if _kept(instruction):
                data[instruction] = InstructionLibraryFragment.create(generator, instruction, extractor)

    library = InstructionLibrary()
    library.data[library.create_key(config, window)] = InstructionLibraryData.create(config, data)
    return library


def _chord(path: Path, config: Config) -> Path:
    audio = sum(
        render_instructions([instruction] * FRAMES, channel_name, config) for channel_name, instruction in CHORD.items()
    )
    write_wave(path, config.library.sample_rate, np.asarray(audio, dtype=np.float32))
    return path


def _joint_config() -> Config:
    config = Config()
    return config.model_copy(
        update={
            "generation": config.generation.model_copy(
                update={
                    "assignment": config.generation.assignment.model_copy(update={"method": AssignmentMethod.JOINT})
                }
            )
        }
    )


@pytest.fixture(name="reconstruction", scope="module")
def reconstruction_fixture(tmp_path_factory: pytest.TempPathFactory) -> Reconstruction:
    config = _joint_config()
    path = _chord(tmp_path_factory.mktemp("chord") / "chord.wav", config)
    reconstructor = Reconstructor(config, frozenset(EVERY_CHANNEL), library=_library(config))
    reconstruction = reconstructor.reconstruct(
        [path], StemsConfig.single_entry(StemSettings(channels=EVERY_CHANNEL, bends=[]))
    )
    assert reconstruction is not None
    return reconstruction


class TestAJointConversionOfAChord:
    def test_the_chord_s_notes_play_on_their_own_kinds_of_channel(self, reconstruction: Reconstruction) -> None:
        instructions = reconstruction.instructions
        held = range(EDGE_FRAMES, FRAMES - EDGE_FRAMES)
        right = 0
        for frame in held:
            pulses = {
                instructions[channel][frame].pitch
                for channel in (ChannelName.PULSE1, ChannelName.PULSE2)
                if isinstance(instructions[channel][frame], PulseInstruction) and instructions[channel][frame].on
            }
            triangle = instructions[ChannelName.TRIANGLE][frame]
            right += (
                pulses == {64, 67}
                and triangle.on
                and isinstance(triangle, TriangleInstruction)
                and triangle.pitch == 48
            )

        assert right >= RIGHT_SHARE * len(held)
