from pathlib import Path
from typing import Final

import numpy as np
import pytest

from sampletones_core.audio import write_wave
from sampletones_core.configs import Config
from sampletones_core.constants.enums import ChannelName, HierarchyMode
from sampletones_core.reconstructions import Reconstructor
from sampletones_core.reconstructions.reconstructor.stems.configs.config import StemsConfig
from sampletones_core.reconstructions.reconstructor.stems.configs.entry import StemEntry
from sampletones_core.reconstructions.reconstructor.stems.configs.hierarchy import StemsHierarchy
from tests.integration.assets.reconstruction import build_mini_library

_TONE_FREQUENCY: Final[float] = 440.0
_DURATION_SECONDS: Final[float] = 0.5


def _stems_config() -> StemsConfig:
    return StemsConfig(
        entries=[
            StemEntry(id=0, channels=[ChannelName.PULSE1]),
            StemEntry(id=1, channels=[ChannelName.NOISE]),
        ],
        hierarchy=StemsHierarchy(
            levels=[[0], [1]],
            mode=HierarchyMode.STRICT,
        ),
        channel_cap=1,
    )


class TestReconstructStems:
    def test_assigns_disjoint_stems_to_their_channels(self, tmp_path: Path) -> None:
        config = Config()
        library = build_mini_library(config)
        reconstructor = Reconstructor(config, library=library)

        sample_rate = config.library.sample_rate
        count = int(sample_rate * _DURATION_SECONDS)
        time = np.arange(count) / sample_rate
        tone = 0.5 * np.sin(2 * np.pi * _TONE_FREQUENCY * time)
        rng = np.random.default_rng(93)
        noise = rng.uniform(-0.3, 0.3, count)

        tone_path = tmp_path / "tone.wav"
        noise_path = tmp_path / "noise.wav"
        write_wave(tone_path, sample_rate, tone)
        write_wave(noise_path, sample_rate, noise)

        reconstruction = reconstructor.reconstruct_stems(
            [tone_path, noise_path],
            _stems_config(),
        )

        assert reconstruction is not None
        assert reconstruction.audio_filepath == (tone_path, noise_path)
        assert reconstruction.stems_data is not None
        stems_data = reconstruction.stems_data
        assert stems_data.config == _stems_config()
        assert {entry.id for entry in stems_data.config.entries} == {0, 1}

        assignments = stems_data.assignments_by_channel
        assert set(assignments) == {
            ChannelName.PULSE1,
            ChannelName.NOISE,
        }
        assert set(assignments[ChannelName.PULSE1]) == {0}
        assert set(assignments[ChannelName.NOISE]) == {1}

        frame_count = count // config.library.frame_length
        assert len(assignments[ChannelName.PULSE1]) == frame_count
        assert len(assignments[ChannelName.NOISE]) == frame_count
        assert len(reconstruction.instructions[ChannelName.PULSE1]) == frame_count
        assert len(reconstruction.instructions[ChannelName.NOISE]) == frame_count

    def test_requires_one_path_per_entry(self, tmp_path: Path) -> None:
        config = Config()
        library = build_mini_library(config)
        reconstructor = Reconstructor(config, library=library)

        with pytest.raises(ValueError, match="stem paths"):
            reconstructor.reconstruct_stems(
                [tmp_path / "only_one.wav"],
                _stems_config(),
            )
