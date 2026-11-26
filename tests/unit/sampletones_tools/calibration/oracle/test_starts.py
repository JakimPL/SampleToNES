from typing import Dict, Final, List

import numpy as np
import pytest

from sampletones_core.configs import Config
from sampletones_core.constants.enums import ChannelName
from sampletones_core.generators import render_channels
from sampletones_core.instructions import InstructionUnion, NoiseInstruction, PulseInstruction, TriangleInstruction
from sampletones_tools.calibration.oracle.starts import started_channels
from tests.suite.base import BaseTestSuite

FRAMES: Final[int] = 6
SEED: Final[int] = 3
OTHER_SEED: Final[int] = 4
TONE: Final[PulseInstruction] = PulseInstruction(on=True, pitch=60, volume=12, duty_cycle=2)
BASS: Final[TriangleInstruction] = TriangleInstruction(on=True, pitch=45)
SHORT_HISS: Final[NoiseInstruction] = NoiseInstruction(on=True, period=4, volume=12, short=True)
LONG_HISS: Final[NoiseInstruction] = NoiseInstruction(on=True, period=4, volume=12, short=False)


def _held(instruction: InstructionUnion) -> List[InstructionUnion]:
    return [instruction] * FRAMES


def _started(instructions: Dict[ChannelName, List[InstructionUnion]], seed: int) -> Dict[ChannelName, np.ndarray]:
    return started_channels(instructions, Config(), np.random.default_rng(seed))


class TestStartedChannels(BaseTestSuite):
    """Each sounding channel plays its frames as a conversion naming them right does, the noise from a state drawn for it."""

    def test_every_sounding_channel_plays_every_frame_and_a_silent_one_renders_nothing(self) -> None:
        silent: List[InstructionUnion] = [PulseInstruction.null_instruction()] * FRAMES

        started = _started({ChannelName.PULSE1: _held(TONE), ChannelName.PULSE2: silent}, SEED)

        assert list(started) == [ChannelName.PULSE1]
        assert started[ChannelName.PULSE1].shape == (FRAMES * Config().library.frame_length,)

    def test_one_draw_renders_alike_every_time(self) -> None:
        instructions = {ChannelName.PULSE1: _held(TONE), ChannelName.NOISE: _held(LONG_HISS)}

        first, second = _started(instructions, SEED), _started(instructions, SEED)

        assert all(np.array_equal(first[channel], second[channel]) for channel in instructions)

    @pytest.mark.parametrize("instruction", [TONE, BASS], ids=["pulse", "triangle"])
    def test_a_tone_plays_from_its_reset_phase_as_the_recording_s_channel_does(
        self, instruction: InstructionUnion
    ) -> None:
        channel = ChannelName.PULSE1 if isinstance(instruction, PulseInstruction) else ChannelName.TRIANGLE

        started = _started({channel: _held(instruction)}, SEED)[channel]

        assert np.array_equal(started, render_channels({channel: _held(instruction)}, Config())[channel])

    @pytest.mark.parametrize("instruction", [LONG_HISS, SHORT_HISS], ids=["long", "short"])
    def test_a_noise_started_elsewhere_plays_another_stretch_of_its_sequence(
        self, instruction: InstructionUnion
    ) -> None:
        """A short noise starts on its own mode's cycle, since a register value off it opens the sequence at its start."""
        first = _started({ChannelName.NOISE: _held(instruction)}, SEED)[ChannelName.NOISE]
        second = _started({ChannelName.NOISE: _held(instruction)}, OTHER_SEED)[ChannelName.NOISE]

        assert not np.array_equal(first, second)
