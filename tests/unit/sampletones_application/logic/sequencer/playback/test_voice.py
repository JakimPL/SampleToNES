from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Final, Iterable, List, Sequence

import numpy as np
import pytest

from sampletones_application.logic.sequencer.playback.synthesizer import SampleVoice
from sampletones_core.configs import Config
from sampletones_core.constants.enums import FeatureKey, GeneratorName
from sampletones_core.constants.general import MAX_VOLUME
from sampletones_core.features import CHANNEL_FEATURE_DEFAULTS
from sampletones_core.instructions import (
    InstructionUnion,
    NoiseInstruction,
    PulseInstruction,
    TriangleInstruction,
)
from sampletones_core.reconstructions import Reconstruction
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase

AUDIO_LENGTH: Final[int] = 64
REFERENCE_PITCH: Final[int] = 60
REFERENCE_PERIOD: Final[int] = 4
SAMPLE_VOLUME: Final[int] = 9
CHANNEL_VOLUME: Final[int] = 4
CHANNEL_ARPEGGIO: Final[int] = 7
CHANNEL_DUTY_CYCLE: Final[int] = 1
CHANNEL_LONG_MODE: Final[int] = 0
DUTY_CYCLE: Final[int] = 2


def _reconstruction(
    generator_name: GeneratorName,
    instructions: Sequence[InstructionUnion],
    held_features: Iterable[FeatureKey],
) -> Reconstruction:
    """A one-channel reconstruction whose instrument leaves ``held_features`` to the channel."""
    reconstruction = Reconstruction.create(
        approximation=np.zeros(AUDIO_LENGTH, dtype=np.float32),
        approximations={generator_name: np.zeros(AUDIO_LENGTH, dtype=np.float32)},
        instructions={generator_name: list(instructions)},
        config=Config(),
        coefficient=1.0,
        audio_filepath=Path("/dev/null"),
    )
    reconstruction.update_generator_data(
        generator_name,
        list(instructions),
        np.ones(AUDIO_LENGTH, dtype=np.float32),
        reconstruction.initial_pitches[generator_name],
        held_features,
    )
    return reconstruction


def _voice(
    generator_name: GeneratorName,
    instructions: Sequence[InstructionUnion],
    held_features: Iterable[FeatureKey],
) -> SampleVoice:
    return SampleVoice.read(_reconstruction(generator_name, instructions, held_features), generator_name)


def _channel_values() -> Dict[FeatureKey, int]:
    return CHANNEL_FEATURE_DEFAULTS.copy()


class TestAFrameSoundsAsTheInstrumentWroteIt(BaseTestSuite):
    """An instrument writing every dimension sounds its frames exactly as it holds them."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        generator_name: GeneratorName
        instructions: List[InstructionUnion]

    test_cases = (
        TestCase(
            label="pulse",
            generator_name=GeneratorName.PULSE1,
            instructions=[
                PulseInstruction(
                    on=True,
                    pitch=REFERENCE_PITCH,
                    volume=SAMPLE_VOLUME,
                    duty_cycle=DUTY_CYCLE,
                )
            ],
        ),
        TestCase(
            label="triangle",
            generator_name=GeneratorName.TRIANGLE,
            instructions=[TriangleInstruction(on=True, pitch=REFERENCE_PITCH)],
        ),
        TestCase(
            label="noise",
            generator_name=GeneratorName.NOISE,
            instructions=[
                NoiseInstruction(
                    on=True,
                    period=REFERENCE_PERIOD,
                    volume=SAMPLE_VOLUME,
                    short=True,
                )
            ],
        ),
    )

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_the_frame_plays_as_it_stands(self, test_case: TestCase) -> None:
        voice = _voice(test_case.generator_name, test_case.instructions, ())

        assert voice.sound(test_case.instructions[0], _channel_values()) == test_case.instructions[0]

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_the_channel_takes_up_what_the_instrument_writes(self, test_case: TestCase) -> None:
        voice = _voice(test_case.generator_name, test_case.instructions, ())
        values = _channel_values()

        voice.sound(test_case.instructions[0], values)

        assert values[FeatureKey.ARPEGGIO] == 0
        assert values[FeatureKey.VOLUME] == (MAX_VOLUME if test_case.label == "triangle" else SAMPLE_VOLUME)


class TestAHeldDimensionSoundsAtTheChannelsValue(BaseTestSuite):
    """A dimension the instrument leaves empty is the channel's, so it sounds at the value it holds.

    Each channel offers its own dimensions and spells them in its own terms — an arpeggio is a
    pitch on pulse and triangle and a period on noise, and a duty cycle is a waveform on pulse and
    the noise mode on noise — so every dimension a channel offers is held here in the terms that
    channel reads it in.
    """

    _INSTRUCTION = PulseInstruction(
        on=True,
        pitch=REFERENCE_PITCH,
        volume=SAMPLE_VOLUME,
        duty_cycle=DUTY_CYCLE,
    )

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        generator_name: GeneratorName
        instruction: InstructionUnion
        held_feature: FeatureKey
        channel_value: int
        expected: InstructionUnion

    test_cases = (
        TestCase(
            label="pulse volume",
            generator_name=GeneratorName.PULSE1,
            instruction=_INSTRUCTION,
            held_feature=FeatureKey.VOLUME,
            channel_value=CHANNEL_VOLUME,
            expected=PulseInstruction(
                on=True,
                pitch=REFERENCE_PITCH,
                volume=CHANNEL_VOLUME,
                duty_cycle=DUTY_CYCLE,
            ),
        ),
        TestCase(
            label="pulse arpeggio",
            generator_name=GeneratorName.PULSE1,
            instruction=_INSTRUCTION,
            held_feature=FeatureKey.ARPEGGIO,
            channel_value=CHANNEL_ARPEGGIO,
            expected=PulseInstruction(
                on=True,
                pitch=REFERENCE_PITCH + CHANNEL_ARPEGGIO,
                volume=SAMPLE_VOLUME,
                duty_cycle=DUTY_CYCLE,
            ),
        ),
        TestCase(
            label="pulse duty cycle",
            generator_name=GeneratorName.PULSE1,
            instruction=_INSTRUCTION,
            held_feature=FeatureKey.DUTY_CYCLE,
            channel_value=CHANNEL_DUTY_CYCLE,
            expected=PulseInstruction(
                on=True,
                pitch=REFERENCE_PITCH,
                volume=SAMPLE_VOLUME,
                duty_cycle=CHANNEL_DUTY_CYCLE,
            ),
        ),
        TestCase(
            label="triangle arpeggio",
            generator_name=GeneratorName.TRIANGLE,
            instruction=TriangleInstruction(on=True, pitch=REFERENCE_PITCH),
            held_feature=FeatureKey.ARPEGGIO,
            channel_value=CHANNEL_ARPEGGIO,
            expected=TriangleInstruction(on=True, pitch=REFERENCE_PITCH + CHANNEL_ARPEGGIO),
        ),
        TestCase(
            label="noise period",
            generator_name=GeneratorName.NOISE,
            instruction=NoiseInstruction(
                on=True,
                period=REFERENCE_PERIOD,
                volume=SAMPLE_VOLUME,
                short=True,
            ),
            held_feature=FeatureKey.ARPEGGIO,
            channel_value=CHANNEL_ARPEGGIO,
            expected=NoiseInstruction(
                on=True,
                period=REFERENCE_PERIOD + CHANNEL_ARPEGGIO,
                volume=SAMPLE_VOLUME,
                short=True,
            ),
        ),
        TestCase(
            label="noise mode",
            generator_name=GeneratorName.NOISE,
            instruction=NoiseInstruction(
                on=True,
                period=REFERENCE_PERIOD,
                volume=SAMPLE_VOLUME,
                short=True,
            ),
            held_feature=FeatureKey.DUTY_CYCLE,
            channel_value=CHANNEL_LONG_MODE,
            expected=NoiseInstruction(
                on=True,
                period=REFERENCE_PERIOD,
                volume=SAMPLE_VOLUME,
                short=False,
            ),
        ),
    )

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_the_frame_sounds_the_channels_value_and_the_instruments_rest(self, test_case: TestCase) -> None:
        voice = _voice(test_case.generator_name, [test_case.instruction], (test_case.held_feature,))
        values = _channel_values()
        values[test_case.held_feature] = test_case.channel_value

        assert voice.sound(test_case.instruction, values) == test_case.expected

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_a_held_dimension_leaves_the_channels_value_where_it_stands(self, test_case: TestCase) -> None:
        voice = _voice(test_case.generator_name, [test_case.instruction], (test_case.held_feature,))
        values = _channel_values()
        values[test_case.held_feature] = test_case.channel_value

        voice.sound(test_case.instruction, values)

        assert values[test_case.held_feature] == test_case.channel_value

    def test_a_level_one_instrument_wrote_is_what_the_next_one_holds(self) -> None:
        """The channel carries a value across samples, which is what makes an empty envelope mean this."""
        writes = _voice(GeneratorName.PULSE1, [self._INSTRUCTION], ())
        holds = _voice(GeneratorName.PULSE1, [self._INSTRUCTION], (FeatureKey.VOLUME,))
        values = _channel_values()

        writes.sound(self._INSTRUCTION, values)

        assert holds.sound(self._INSTRUCTION, values).volume == SAMPLE_VOLUME

    def test_an_instrument_holding_its_level_sounds_a_silent_frame(self) -> None:
        """Silence is stated by a volume envelope, so an instrument leaving one out plays on."""
        rest = PulseInstruction.null_instruction()
        voice = _voice(GeneratorName.PULSE1, [self._INSTRUCTION, rest], (FeatureKey.VOLUME,))

        assert voice.sound(rest, _channel_values()).on is True

    def test_a_silent_frame_takes_the_channel_to_silence_where_the_instrument_writes_its_level(self) -> None:
        rest = PulseInstruction.null_instruction()
        voice = _voice(GeneratorName.PULSE1, [self._INSTRUCTION, rest], ())
        values = _channel_values()

        assert voice.sound(rest, values).on is False
        assert values[FeatureKey.VOLUME] == 0

    def test_a_silent_frame_leaves_the_other_dimensions_where_the_channel_holds_them(self) -> None:
        rest = PulseInstruction.null_instruction()
        voice = _voice(GeneratorName.PULSE1, [self._INSTRUCTION, rest], ())
        values = _channel_values()
        values[FeatureKey.DUTY_CYCLE] = DUTY_CYCLE

        voice.sound(rest, values)

        assert values[FeatureKey.DUTY_CYCLE] == DUTY_CYCLE
