from typing import Final

import numpy as np

from sampletones_application.logic.shared.synthesis import ChannelBank, EngineRates, synthesize_tick
from sampletones_core.configs import Config
from sampletones_core.constants.audio import DEFAULT_SAMPLE_RATE
from sampletones_core.constants.enums import ChannelName
from sampletones_core.instructions import PulseInstruction

FRAME_LENGTH: Final[int] = 735
SHORTER_FRAME: Final[int] = 734
INSTRUCTION: Final[PulseInstruction] = PulseInstruction(on=True, pitch=60, volume=15, duty_cycle=2)


def _bank() -> ChannelBank:
    return ChannelBank(Config(), EngineRates(nes_frequency=60, sample_rate=DEFAULT_SAMPLE_RATE))


class TestOneTick:
    """A tick sounds its instruction for the samples the clock gives it, and a resting channel sounds silence."""

    def test_an_instruction_sounds_for_the_tick_it_is_given(self) -> None:
        generator = _bank().generator(ChannelName.PULSE1)

        audio = synthesize_tick(generator, INSTRUCTION, SHORTER_FRAME)

        assert len(audio) == SHORTER_FRAME
        assert np.any(audio)
        assert generator.frame_length == SHORTER_FRAME

    def test_a_resting_channel_sounds_silence_and_leaves_its_generator_alone(self) -> None:
        generator = _bank().generator(ChannelName.PULSE1)
        standing = generator.frame_length

        audio = synthesize_tick(generator, None, SHORTER_FRAME)

        assert len(audio) == SHORTER_FRAME
        assert not np.any(audio)
        assert generator.frame_length == standing

    def test_a_held_note_carries_its_phase_into_the_next_tick(self) -> None:
        held = _bank().generator(ChannelName.PULSE1)
        fresh = _bank().generator(ChannelName.PULSE1)
        synthesize_tick(held, INSTRUCTION, FRAME_LENGTH)

        second = synthesize_tick(held, INSTRUCTION, FRAME_LENGTH)
        first_of_fresh = synthesize_tick(fresh, INSTRUCTION, FRAME_LENGTH)

        assert not np.array_equal(second, first_of_fresh)
