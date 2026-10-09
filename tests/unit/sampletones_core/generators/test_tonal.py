import math
from typing import Final

import pytest

from sampletones_core.configs import Config
from sampletones_core.constants.enums import ChannelName
from sampletones_core.constants.general import (
    HI_PITCH_FACTOR,
    MAX_PITCH,
    MAX_TIMER,
    MIN_TIMER,
)
from sampletones_core.generators.implementation.pulse import PulseGenerator
from sampletones_core.generators.implementation.triangle import TriangleGenerator
from sampletones_core.instructions import PulseInstruction, TriangleInstruction

PITCH: Final[int] = 60
VOLUME: Final[int] = 15
CENTS_PER_OCTAVE: Final[float] = 1200.0


@pytest.fixture
def config() -> Config:
    return Config()


@pytest.fixture
def generator(config: Config) -> PulseGenerator:
    return PulseGenerator(config, ChannelName.PULSE1)


def _pulse(**bend: int) -> PulseInstruction:
    return PulseInstruction(on=True, pitch=PITCH, volume=VOLUME, duty_cycle=0, **bend)


class TestBendingTheDivider:
    def test_an_unbent_frame_sounds_at_the_note_itself(self, generator: PulseGenerator) -> None:
        generator.set_timer(_pulse())

        assert generator.timer.timer == generator.timer_table[PITCH]

    def test_a_bend_moves_the_divider_by_the_steps_it_states(self, generator: PulseGenerator) -> None:
        generator.set_timer(_pulse(detune=5, coarse_detune=1))

        assert generator.timer.timer == generator.timer_table[PITCH] + 5 + HI_PITCH_FACTOR

    def test_a_larger_divider_sounds_lower(self, generator: PulseGenerator) -> None:
        """The divider counts a period, so adding to it lowers the note the frame sounds."""
        generator.set_timer(_pulse())
        unbent = generator.timer.frequency

        generator.set_timer(_pulse(detune=1))

        assert generator.timer.frequency < unbent

    def test_a_bend_of_a_whole_gap_reaches_the_neighboring_note(self, generator: PulseGenerator) -> None:
        gap = generator.timer_table[PITCH] - generator.timer_table[PITCH + 1]
        generator.set_timer(_pulse(detune=-gap))

        assert generator.timer.timer == generator.timer_table[PITCH + 1]

    def test_one_step_is_finer_than_a_semitone_in_the_middle_register(
        self,
        generator: PulseGenerator,
    ) -> None:
        """A step spans a fraction of the gap to the next note, which is the room a bend has."""
        generator.set_timer(_pulse())
        unbent = generator.timer.frequency
        generator.set_timer(_pulse(detune=1))
        stepped = generator.timer.frequency

        cents = abs(CENTS_PER_OCTAVE * math.log2(stepped / unbent))
        semitone = CENTS_PER_OCTAVE / 12

        assert 0.0 < cents < semitone


class TestBendClamping:
    def test_a_bend_below_the_register_is_held_at_its_floor(self, generator: PulseGenerator) -> None:
        generator.set_timer(PulseInstruction(on=True, pitch=MAX_PITCH, volume=VOLUME, duty_cycle=0, coarse_detune=-8))

        assert generator.timer.timer == MIN_TIMER

    def test_a_bend_past_the_register_is_held_at_its_ceiling(self, config: Config) -> None:
        generator = PulseGenerator(config, ChannelName.PULSE1)
        lowest = min(generator.timer_table)
        generator.set_timer(PulseInstruction(on=True, pitch=lowest, volume=VOLUME, duty_cycle=0, coarse_detune=127))

        assert generator.timer.timer == MAX_TIMER

    def test_a_silent_frame_carries_no_bend_into_the_timer(self, generator: PulseGenerator) -> None:
        generator.set_timer(PulseInstruction(on=False, pitch=PITCH, volume=0, duty_cycle=0, detune=40))

        assert generator.timer.frequency == 0.0 or generator.timer.timer == 0


class TestTriangleBend:
    def test_the_triangle_bends_through_the_same_table(self, config: Config) -> None:
        generator = TriangleGenerator(config, ChannelName.TRIANGLE)

        generator.set_timer(TriangleInstruction(on=True, pitch=PITCH, detune=-3))

        assert generator.timer.timer == generator.timer_table[PITCH] - 3
