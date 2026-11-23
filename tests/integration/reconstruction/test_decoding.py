from pathlib import Path
from typing import AbstractSet, Dict, Final, FrozenSet, List, assert_never

import numpy as np
import pytest

from sampletones_core.audio import write_wave
from sampletones_core.configs import Config
from sampletones_core.configs.generation import AssignmentConfig, DecoderConfig, GenerationConfig
from sampletones_core.constants.enums import (
    DEFAULT_CHANNELS,
    AssignmentMethod,
    ChannelName,
    SelectorName,
)
from sampletones_core.generators.implementation.triangle import TriangleGenerator
from sampletones_core.instructions import InstructionUnion
from sampletones_core.library import InstructionLibrary
from sampletones_core.reconstructions import Reconstruction, Reconstructor
from sampletones_tools.corpus.catalog import build_mini_library

_FRAMES: Final[int] = 60
_LOWER_NOTE: Final[int] = 78
_UNBENT: Final[int] = 0
_HALFWAY: Final[float] = 0.5
_SWING: Final[float] = 0.02
_SWING_DIRECTIONS: Final[List[float]] = [-1.0, 1.0]
_LEVEL: Final[float] = 0.5
_TRIANGLE: Final[FrozenSet[ChannelName]] = frozenset({ChannelName.TRIANGLE})
_EVERY_CHANNEL: Final[FrozenSet[ChannelName]] = frozenset(DEFAULT_CHANNELS)


def _swinging_shares() -> np.ndarray:
    """How far each frame's pitch stands from the lower note toward the upper one, as a share of the step."""
    return _HALFWAY + _SWING * np.resize(_SWING_DIRECTIONS, _FRAMES)


def _wavering_tone(config: Config) -> np.ndarray:
    """A sine halfway between two neighboring triangle notes, swinging a small share of the step toward
    one note and then the other, a frame's length at a time.

    Every frame lies nearer one of the notes, so the cheapest candidate flips from frame to frame. Every
    frame lies almost as near the other note, so a note held through the swing loses less on each frame it
    misses than the two changes of note it spares there, at the pitch weight a decoder weighing transitions
    charges. The notes stand where the triangle generator sounds them.
    """
    generator = TriangleGenerator(config)
    lower = generator.sounds_at(_LOWER_NOTE, _UNBENT)
    upper = generator.sounds_at(_LOWER_NOTE + 1, _UNBENT)
    frame_frequencies = lower * (upper / lower) ** _swinging_shares()
    sample_frequencies = np.repeat(frame_frequencies, config.library.frame_length)
    phase = 2 * np.pi * np.cumsum(sample_frequencies) / config.library.sample_rate
    return _LEVEL * np.sin(phase)


def _assignment_read_by(selector_name: SelectorName) -> AssignmentMethod:
    """The assignment offering what ``selector_name`` decodes.

    The combinations decoder reads the whole combinations only the joint assignment pools. The greedy and
    the Viterbi decoders read every channel's columns, which the picks assignment offers.
    """
    match selector_name:
        case SelectorName.COMBINATIONS:
            return AssignmentMethod.JOINT
        case SelectorName.GREEDY | SelectorName.VITERBI:
            return AssignmentMethod.PICKS
        case _:
            assert_never(selector_name)


def _config(selector_name: SelectorName) -> Config:
    """The configuration decoding with ``selector_name``, its frames assigned the way that decoder reads them."""
    return Config(
        generation=GenerationConfig(
            assignment=AssignmentConfig(method=_assignment_read_by(selector_name)),
            decoder=DecoderConfig(selector=selector_name),
        )
    )


def _reconstruct(
    selector_name: SelectorName,
    channels: AbstractSet[ChannelName],
    audio_path: Path,
    library: InstructionLibrary,
) -> Reconstruction:
    reconstruction = Reconstructor(_config(selector_name), channels, library=library)(audio_path)
    assert reconstruction is not None
    return reconstruction


def _changes(stream: List[InstructionUnion]) -> int:
    return sum(1 for previous, current in zip(stream, stream[1:]) if previous != current)


def _change_counts(reconstruction: Reconstruction) -> Dict[ChannelName, int]:
    return {
        channel_name: _changes(reconstruction.instructions[channel_name])
        for channel_name in reconstruction.playing_channels
    }


@pytest.fixture(name="library", scope="module")
def library_fixture() -> InstructionLibrary:
    return build_mini_library(Config())


@pytest.fixture(name="wavering_path", scope="module")
def wavering_path_fixture(tmp_path_factory: pytest.TempPathFactory) -> Path:
    config = Config()
    path = tmp_path_factory.mktemp("decoding") / "wavering.wav"
    write_wave(path, config.library.sample_rate, _wavering_tone(config))
    return path


@pytest.fixture(name="greedy", scope="module")
def greedy_fixture(wavering_path: Path, library: InstructionLibrary) -> Reconstruction:
    """The wavering tone decoded frame by frame on the triangle, the channel whose notes it swings between."""
    return _reconstruct(SelectorName.GREEDY, _TRIANGLE, wavering_path, library)


@pytest.fixture(name="viterbi", scope="module")
def viterbi_fixture(wavering_path: Path, library: InstructionLibrary) -> Reconstruction:
    """The wavering tone decoded on the triangle with its transitions weighed."""
    return _reconstruct(SelectorName.VITERBI, _TRIANGLE, wavering_path, library)


class TestConfiguredDecoderReachesTheConversion:
    """The decoder named in the configuration is the one a conversion is decoded with."""

    def test_the_two_decoders_answer_the_same_target_differently(
        self,
        greedy: Reconstruction,
        viterbi: Reconstruction,
    ) -> None:
        assert set(greedy.playing_channels) == set(viterbi.playing_channels)
        assert any(
            greedy.instructions[channel_name] != viterbi.instructions[channel_name]
            for channel_name in greedy.playing_channels
        )

    def test_continuity_decoding_holds_instructions_longer(
        self,
        greedy: Reconstruction,
        viterbi: Reconstruction,
    ) -> None:
        """Weighing transitions is what buys steadiness, so the decoded streams change less often."""
        assert sum(_change_counts(viterbi).values()) < sum(_change_counts(greedy).values())

    def test_a_decoder_answers_every_frame_of_every_channel(
        self,
        wavering_path: Path,
        library: InstructionLibrary,
    ) -> None:
        for selector_name in SelectorName:
            reconstruction = _reconstruct(selector_name, _EVERY_CHANNEL, wavering_path, library)
            frame_counts = {
                channel_name: len(reconstruction.instructions[channel_name])
                for channel_name in reconstruction.playing_channels
            }
            assert len(set(frame_counts.values())) == 1
            assert set(reconstruction.stems_data.assignments_by_channel) == set(reconstruction.playing_channels)
            for channel_name, stem_ids in reconstruction.stems_data.assignments_by_channel.items():
                assert len(stem_ids) == frame_counts[channel_name]
