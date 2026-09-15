from pathlib import Path
from typing import Any, Dict, Final, FrozenSet, List

import numpy as np
import pytest

from sampletones_core.audio import write_wave
from sampletones_core.configs import Config
from sampletones_core.constants.enums import ChannelName, SpectrumMethod
from sampletones_core.fft import Window
from sampletones_core.fft.features import get_feature_extractor
from sampletones_core.generators import get_generators_by_channels
from sampletones_core.instructions import InstructionUnion, NoiseInstruction, PulseInstruction, TriangleInstruction
from sampletones_core.library import InstructionLibrary, InstructionLibraryData, InstructionLibraryFragment
from sampletones_core.reconstructions import Reconstruction, Reconstructor
from sampletones_core.reconstructions.reconstructor.stems.configs.config import StemsConfig
from tests.suite.analysis import analyzed_config

EVERY_CHANNEL: Final[List[ChannelName]] = [ChannelName.PULSE1, ChannelName.TRIANGLE, ChannelName.NOISE]
TONE_FREQUENCY: Final[float] = 220.0
TONE_AMPLITUDE: Final[float] = 0.5
TONE_SECONDS: Final[float] = 0.5
TRIANGLE_PITCHES: Final[range] = range(67, 72)
PULSE_PITCHES: Final[FrozenSet[int]] = frozenset({*range(55, 60), *range(67, 72)})
VOLUMES: Final[FrozenSet[int]] = frozenset({1, 8, 15})
NOISE_PERIODS: Final[FrozenSet[int]] = frozenset({0, 4, 8, 12, 15})
EDGE_FRAMES: Final[int] = 2


def _library(config: Config) -> InstructionLibrary:
    """The notes around a tone on both tone channels beside the noise, at a spread of volumes and periods."""
    window = Window.from_config(config)
    extractor = get_feature_extractor(config, window)

    data: Dict[InstructionUnion, InstructionLibraryFragment[Any]] = {}
    for generator in get_generators_by_channels(config, EVERY_CHANNEL).values():
        for instruction in generator.get_possible_instructions():
            if _kept(instruction):
                data[instruction] = InstructionLibraryFragment.create(generator, instruction, extractor)

    library = InstructionLibrary()
    library.data[library.create_key(config, window)] = InstructionLibraryData.create(config, data)
    return library


def _kept(instruction: InstructionUnion) -> bool:
    if not instruction.on:
        return True

    match instruction:
        case TriangleInstruction():
            return instruction.pitch in TRIANGLE_PITCHES
        case PulseInstruction():
            return instruction.pitch in PULSE_PITCHES and instruction.volume in VOLUMES
        case NoiseInstruction():
            return instruction.volume in VOLUMES and instruction.period in NOISE_PERIODS
        case _:
            return False


def _tone(path: Path, config: Config) -> Path:
    sample_rate = config.library.sample_rate
    time = np.arange(int(sample_rate * TONE_SECONDS)) / sample_rate
    write_wave(path, sample_rate, TONE_AMPLITUDE * np.sin(2.0 * np.pi * TONE_FREQUENCY * time))
    return path


@pytest.fixture(
    scope="module",
    params=[SpectrumMethod.FFT, SpectrumMethod.CQT],
    ids=lambda method: method.value,
)
def reconstructed_tone(request: pytest.FixtureRequest, tmp_path_factory: pytest.TempPathFactory) -> Reconstruction:
    config = analyzed_config(request.param, gamma=Config().library.transformation_gamma)
    path = _tone(tmp_path_factory.mktemp("tone") / "tone.wav", config)
    reconstructor = Reconstructor(config, frozenset(EVERY_CHANNEL), library=_library(config))
    reconstruction = reconstructor.reconstruct([path], StemsConfig.single_entry(EVERY_CHANNEL, []))
    assert reconstruction is not None
    return reconstruction


class TestASineBecomesOneTriangle:
    """
    A steady sine at the working level is what the triangle renders whole, so the frame's cost
    falls to its lowest with the triangle alone: a pulse or the noise added beside it raises the
    cost, and those channels hold their silence through the tone.
    """

    def test_the_triangle_sounds_through_the_tone(self, reconstructed_tone: Reconstruction) -> None:
        interior = reconstructed_tone.instructions[ChannelName.TRIANGLE][EDGE_FRAMES:-EDGE_FRAMES]
        assert all(instruction.on for instruction in interior)

    def test_no_other_channel_sounds_within_the_tone(self, reconstructed_tone: Reconstruction) -> None:
        for channel_name in reconstructed_tone.playing_channels:
            if channel_name == ChannelName.TRIANGLE:
                continue

            interior = reconstructed_tone.instructions[channel_name][EDGE_FRAMES:-EDGE_FRAMES]
            assert not any(instruction.on for instruction in interior), channel_name
