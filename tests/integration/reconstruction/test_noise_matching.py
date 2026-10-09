from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Final, List

import numpy as np
import pytest

from sampletones_core.audio import write_wave
from sampletones_core.configs import Config
from sampletones_core.constants.algorithm import STEM_ACTIVITY_FLOOR
from sampletones_core.constants.enums import ChannelName, SpectrumMethod
from sampletones_core.constants.general import NUM_PERIODS
from sampletones_core.fft import Window
from sampletones_core.fft.features import get_feature_extractor
from sampletones_core.generators import get_generators_by_channels
from sampletones_core.instructions import InstructionUnion
from sampletones_core.library import (
    InstructionLibrary,
    InstructionLibraryData,
    InstructionLibraryFragment,
)
from sampletones_core.reconstructions import Reconstructor
from sampletones_core.reconstructions.reconstructor.stems.configs.config import StemsConfig
from sampletones_core.reconstructions.reconstructor.stems.configs.settings import StemSettings
from sampletones_tools.synthesis.oscillators.walk_noise import WalkNoiseOscillator
from tests.suite.analysis import analyzed_config
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase

NOISE_ONLY: Final[List[ChannelName]] = [ChannelName.NOISE]
EVERY_CHANNEL: Final[List[ChannelName]] = ChannelName.items()
LIBRARY_CHANNELS: Final[List[ChannelName]] = [ChannelName.PULSE1, ChannelName.TRIANGLE, ChannelName.NOISE]
TONAL_PITCH: Final[int] = 69
TONAL_NEIGHBORHOOD: Final[range] = range(TONAL_PITCH - 2, TONAL_PITCH + 3)
NOISE_RECORDING_SEED: Final[int] = 11
WHITE_NOISE_DEVIATION: Final[float] = 0.3
NOISE_SECONDS: Final[float] = 1.0
DARK_NOISE_PEAK: Final[float] = 0.9
EDGE_FRAMES: Final[int] = 1
QUIET_VOLUMES: Final[range] = range(1, 4)
LOUD_VOLUMES: Final[range] = range(12, 16)
SHORTEST_PERIODS: Final[range] = range(NUM_PERIODS - 4, NUM_PERIODS)
NOISE_SEED: Final[int] = 5
BURST_FRAMES: Final[int] = 12
GAP_FRAMES: Final[int] = 6
HISS_FRAMES: Final[int] = 24
BURST_DEVIATION: Final[float] = 0.3
HISS_DEVIATION: Final[float] = BURST_DEVIATION / 11.0
HISS: Final[slice] = slice(BURST_FRAMES + GAP_FRAMES, BURST_FRAMES + GAP_FRAMES + HISS_FRAMES)


NoiseBuilder = Callable[[np.ndarray, np.random.Generator], np.ndarray]


@dataclass(frozen=True)
class Converted:
    hiss_frames: np.ndarray
    instructions: List[InstructionUnion]


@dataclass(frozen=True)
class Analysis:
    config: Config
    library: InstructionLibrary


def _config(method: SpectrumMethod) -> Config:
    return analyzed_config(method, gamma=Config().library.transformation_gamma)


def _library(config: Config) -> InstructionLibrary:
    """The noise channel's silence and its quietest and loudest instructions at the shortest periods,
    so a burst and a hiss both find the noise standing nearest them."""
    window = Window.from_config(config)
    extractor = get_feature_extractor(config, window)
    generator = get_generators_by_channels(config, NOISE_ONLY)[ChannelName.NOISE]

    data: Dict[InstructionUnion, InstructionLibraryFragment[Any]] = {
        instruction: InstructionLibraryFragment.create(generator, instruction, extractor)
        for instruction in generator.get_possible_instructions()
        if not instruction.on
        or (instruction.volume in (*QUIET_VOLUMES, *LOUD_VOLUMES) and instruction.period in SHORTEST_PERIODS)
    }

    library = InstructionLibrary()
    library.data[library.create_key(config, window)] = InstructionLibraryData.create(config, data)
    return library


def _burst_then_hiss(path: Path, config: Config) -> Path:
    """A noise burst setting the working level, a silent gap, then a hiss far quieter than the burst."""
    frame_length = config.library.frame_length
    generator = np.random.default_rng(NOISE_SEED)
    audio = np.concatenate(
        [
            generator.normal(0.0, BURST_DEVIATION, frame_length * BURST_FRAMES),
            np.zeros(frame_length * GAP_FRAMES),
            generator.normal(0.0, HISS_DEVIATION, frame_length * HISS_FRAMES),
        ]
    )

    write_wave(path, config.library.sample_rate, audio)
    return path


def _every_channel_library(config: Config) -> InstructionLibrary:
    """Every noise instruction beside the notes around one pitch, so a tonal answer stands within reach.

    Both pulse channels play the pulse instructions, so the first pulse channel's instructions
    serve the second.
    """
    window = Window.from_config(config)
    extractor = get_feature_extractor(config, window)

    data: Dict[InstructionUnion, InstructionLibraryFragment[Any]] = {}
    for channel_name, generator in get_generators_by_channels(config, LIBRARY_CHANNELS).items():
        for instruction in generator.get_possible_instructions():
            if channel_name != ChannelName.NOISE and instruction.on and instruction.pitch not in TONAL_NEIGHBORHOOD:
                continue

            data[instruction] = InstructionLibraryFragment.create(generator, instruction, extractor)

    library = InstructionLibrary()
    library.data[library.create_key(config, window)] = InstructionLibraryData.create(config, data)
    return library


def _white_noise(time: np.ndarray, generator: np.random.Generator) -> np.ndarray:
    return generator.normal(0.0, WHITE_NOISE_DEVIATION, time.shape[0])


def _dark_noise(time: np.ndarray, generator: np.random.Generator) -> np.ndarray:
    return DARK_NOISE_PEAK * WalkNoiseOscillator(kind="walk_noise").render(time, generator=generator)


def _noise_recording(path: Path, config: Config, noise: NoiseBuilder) -> Path:
    sample_rate = config.library.sample_rate
    time = np.arange(int(sample_rate * NOISE_SECONDS)) / sample_rate
    write_wave(path, sample_rate, noise(time, np.random.default_rng(NOISE_RECORDING_SEED)))
    return path


@pytest.fixture(
    scope="module",
    params=list(SpectrumMethod),
    ids=lambda method: method.value,
)
def converted(
    request: pytest.FixtureRequest,
    tmp_path_factory: pytest.TempPathFactory,
) -> Converted:
    """A burst, a gap and a hiss reconstructed on the noise channel alone, once per spectrum method."""
    config = _config(request.param)
    path = _burst_then_hiss(tmp_path_factory.mktemp("hiss") / "hiss.wav", config)
    reconstructor = Reconstructor(config, frozenset(NOISE_ONLY), library=_library(config))
    reconstruction = reconstructor.reconstruct(
        [path], StemsConfig.single_entry(StemSettings(channels=NOISE_ONLY, bends=[]))
    )
    assert reconstruction is not None

    frame_length = config.library.frame_length
    working_level = reconstructor.load_audio(path) / reconstruction.coefficient
    return Converted(
        hiss_frames=working_level[frame_length * HISS.start : frame_length * HISS.stop].reshape(HISS_FRAMES, -1),
        instructions=reconstruction.instructions[ChannelName.NOISE],
    )


@pytest.fixture(
    scope="module",
    params=list(SpectrumMethod),
    ids=lambda method: method.value,
)
def every_channel_analysis(request: pytest.FixtureRequest) -> Analysis:
    """Every channel's library under one spectrum method, shared by every noise reconstructed with it."""
    config = _config(request.param)
    return Analysis(config=config, library=_every_channel_library(config))


class TestNoiseSoundsOnTheNoiseChannel(BaseTestSuite):
    """
    A recording built from noise reconstructs with the noise channel sounding, with every channel
    offered and under every spectrum method. Noise resembles the noise channel's contribution on
    average, so the noise channel carries it through, whether the noise is white or dark.
    """

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        noise: NoiseBuilder

    test_cases = (
        TestCase(label="white", noise=_white_noise),
        TestCase(label="dark", noise=_dark_noise),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_noise_channel_sounds(
        self,
        test_case: TestCase,
        every_channel_analysis: Analysis,
        tmp_path: Path,
    ) -> None:
        config = every_channel_analysis.config
        path = _noise_recording(tmp_path / f"{test_case.label}.wav", config, test_case.noise)
        reconstructor = Reconstructor(config, frozenset(EVERY_CHANNEL), library=every_channel_analysis.library)

        reconstruction = reconstructor.reconstruct(
            [path], StemsConfig.single_entry(StemSettings(channels=EVERY_CHANNEL, bends=[]))
        )

        assert reconstruction is not None
        interior = reconstruction.instructions[ChannelName.NOISE][EDGE_FRAMES:-EDGE_FRAMES]
        assert all(instruction.on for instruction in interior)


class TestAHissAfterABurst:
    """
    The working level brings the burst to the noise channel's full-scale level, and the hiss keeps
    its distance below it, which lands among the quietest volumes the channel plays. The gap before
    it leaves the channel resting, so the hiss is what decides whether the channel sounds.
    """

    def test_every_hiss_frame_passes_the_activity_gate(self, converted: Converted) -> None:
        assert float(np.abs(converted.hiss_frames).max(axis=1).min()) >= STEM_ACTIVITY_FLOOR

    def test_the_burst_sounds_on_the_noise_channel(self, converted: Converted) -> None:
        assert all(instruction.on for instruction in converted.instructions[:BURST_FRAMES])

    def test_the_hiss_sounds_quieter_than_the_burst(self, converted: Converted) -> None:
        burst_volume = max(instruction.volume for instruction in converted.instructions[:BURST_FRAMES])
        hiss = converted.instructions[HISS]

        assert all(instruction.on for instruction in hiss)
        assert all(instruction.volume < burst_volume for instruction in hiss)
