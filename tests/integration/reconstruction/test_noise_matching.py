from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Final, List

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

NOISE_ONLY: Final[List[ChannelName]] = [ChannelName.NOISE]
QUIET_VOLUMES: Final[range] = range(1, 4)
SHORTEST_PERIODS: Final[range] = range(NUM_PERIODS - 4, NUM_PERIODS)
NOISE_SEED: Final[int] = 5
BURST_FRAMES: Final[int] = 12
GAP_FRAMES: Final[int] = 6
HISS_FRAMES: Final[int] = 24
BURST_DEVIATION: Final[float] = 0.3
HISS_DEVIATION: Final[float] = BURST_DEVIATION / 11.0
HISS: Final[slice] = slice(BURST_FRAMES + GAP_FRAMES, BURST_FRAMES + GAP_FRAMES + HISS_FRAMES)


@dataclass(frozen=True)
class Converted:
    hiss_frames: np.ndarray
    instructions: List[InstructionUnion]


def _config(method: SpectrumMethod) -> Config:
    base = Config()
    return base.model_copy(update={"library": base.library.model_copy(update={"spectrum_method": method})})


def _library(config: Config) -> InstructionLibrary:
    """The noise channel's silence and its quietest instructions at the shortest periods, the noise
    standing nearest a hiss."""
    window = Window.from_config(config)
    extractor = get_feature_extractor(config, window)
    generator = get_generators_by_channels(config, NOISE_ONLY)[ChannelName.NOISE]

    data: Dict[InstructionUnion, InstructionLibraryFragment[Any]] = {
        instruction: InstructionLibraryFragment.create(generator, instruction, extractor)
        for instruction in generator.get_possible_instructions()
        if not instruction.on or (instruction.volume in QUIET_VOLUMES and instruction.period in SHORTEST_PERIODS)
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


class TestAHissBelowTheSpectrumFloor:
    """
    A hiss loud enough to pass the activity gate lies far below the spectrum floor at the working
    level, where the noise the channel plays stands further from it than silence does. The gap
    before it leaves the channel resting, so the hiss is what decides whether the channel sounds.
    """

    @pytest.fixture(
        scope="class",
        params=list(SpectrumMethod),
        ids=lambda method: method.value,
    )
    def converted(
        self,
        request: pytest.FixtureRequest,
        tmp_path_factory: pytest.TempPathFactory,
    ) -> Converted:
        config = _config(request.param)
        path = _burst_then_hiss(tmp_path_factory.mktemp("hiss") / "hiss.wav", config)
        reconstructor = Reconstructor(config, frozenset(NOISE_ONLY), library=_library(config))
        reconstruction = reconstructor.reconstruct([path], StemsConfig.single_entry(NOISE_ONLY, []))
        assert reconstruction is not None

        frame_length = config.library.frame_length
        working_level = reconstructor.load_audio(path) / reconstruction.coefficient
        return Converted(
            hiss_frames=working_level[frame_length * HISS.start : frame_length * HISS.stop].reshape(HISS_FRAMES, -1),
            instructions=reconstruction.instructions[ChannelName.NOISE],
        )

    def test_every_hiss_frame_passes_the_activity_gate(self, converted: Converted) -> None:
        assert float(np.abs(converted.hiss_frames).max(axis=1).min()) >= STEM_ACTIVITY_FLOOR

    def test_the_burst_sounds_on_the_noise_channel(self, converted: Converted) -> None:
        assert all(instruction.on for instruction in converted.instructions[:BURST_FRAMES])

    def test_the_hiss_leaves_the_noise_channel_silent(self, converted: Converted) -> None:
        assert not any(instruction.on for instruction in converted.instructions[HISS])
