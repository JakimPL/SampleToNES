from pathlib import Path
from typing import Dict, Final, List

import numpy as np

from sampletones_core.audio import write_wave
from sampletones_core.configs import Config
from sampletones_core.configs.generation import GenerationConfig
from sampletones_core.constants.enums import ChannelName, SelectorName
from sampletones_core.instructions import InstructionUnion
from sampletones_core.reconstructions import Reconstruction, Reconstructor
from tests.integration.assets.reconstruction import build_mini_library

_DURATION_SECONDS: Final[float] = 1.0
_LOWER_TONE: Final[float] = 440.0
_UPPER_TONE: Final[float] = 661.0
_NOISE_LEVEL: Final[float] = 0.08
_NOISE_SEED: Final[int] = 17


def _flickering_path(tmp_path: Path, config: Config) -> Path:
    """A two-tone target under light noise, so the cheapest candidate wavers frame to frame."""
    sample_rate = config.library.sample_rate
    count = int(sample_rate * _DURATION_SECONDS)
    time = np.arange(count) / sample_rate
    audio = 0.5 * np.sin(2 * np.pi * _LOWER_TONE * time) + 0.25 * np.sin(2 * np.pi * _UPPER_TONE * time)
    audio += np.random.default_rng(_NOISE_SEED).normal(0.0, _NOISE_LEVEL, count)

    path = tmp_path / "flicker.wav"
    write_wave(path, sample_rate, audio)
    return path


def _reconstruct(selector_name: SelectorName, audio_path: Path) -> Reconstruction:
    config = Config(generation=GenerationConfig(decoder={"selector": selector_name}))
    reconstruction = Reconstructor(config, library=build_mini_library(config))(audio_path)
    assert reconstruction is not None
    return reconstruction


def _changes(stream: List[InstructionUnion]) -> int:
    return sum(1 for previous, current in zip(stream, stream[1:]) if previous != current)


def _change_counts(reconstruction: Reconstruction) -> Dict[ChannelName, int]:
    return {
        channel_name: _changes(reconstruction.instructions[channel_name])
        for channel_name in reconstruction.playing_channels
    }


class TestConfiguredDecoderReachesTheConversion:
    """The decoder named in the configuration is the one a conversion is decoded with."""

    def test_the_two_decoders_answer_the_same_target_differently(self, tmp_path: Path) -> None:
        audio_path = _flickering_path(tmp_path, Config())

        greedy = _reconstruct(SelectorName.GREEDY, audio_path)
        viterbi = _reconstruct(SelectorName.VITERBI, audio_path)

        assert set(greedy.playing_channels) == set(viterbi.playing_channels)
        assert any(
            greedy.instructions[channel_name] != viterbi.instructions[channel_name]
            for channel_name in greedy.playing_channels
        )

    def test_continuity_decoding_holds_instructions_longer(self, tmp_path: Path) -> None:
        """Weighing transitions is what buys steadiness, so the decoded streams change less often."""
        audio_path = _flickering_path(tmp_path, Config())

        greedy = _reconstruct(SelectorName.GREEDY, audio_path)
        viterbi = _reconstruct(SelectorName.VITERBI, audio_path)

        assert sum(_change_counts(viterbi).values()) < sum(_change_counts(greedy).values())

    def test_a_decoder_answers_every_frame_of_every_channel(self, tmp_path: Path) -> None:
        audio_path = _flickering_path(tmp_path, Config())

        for selector_name in SelectorName:
            reconstruction = _reconstruct(selector_name, audio_path)
            frame_counts = {
                channel_name: len(reconstruction.instructions[channel_name])
                for channel_name in reconstruction.playing_channels
            }
            assert len(set(frame_counts.values())) == 1
            assert set(reconstruction.stems_data.assignments_by_channel) == set(reconstruction.playing_channels)
            for channel_name, stem_ids in reconstruction.stems_data.assignments_by_channel.items():
                assert len(stem_ids) == frame_counts[channel_name]
