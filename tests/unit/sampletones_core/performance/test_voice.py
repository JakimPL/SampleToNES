from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Final, FrozenSet, Iterable, List, Sequence

import numpy as np
import pytest

from sampletones_core.configs import Config
from sampletones_core.constants.enums import (
    DEFAULT_CHANNELS,
    ChannelName,
    FeatureKey,
)
from sampletones_core.constants.general import MAX_VOLUME
from sampletones_core.features import CHANNEL_FEATURE_DEFAULTS
from sampletones_core.features.envelope import Envelope
from sampletones_core.instructions import (
    InstructionUnion,
    NoiseInstruction,
    PulseInstruction,
    TriangleInstruction,
)
from sampletones_core.performance import VoiceReading, heard_readings
from sampletones_core.project.voices.envelopes import InstrumentEnvelopes
from sampletones_core.project.voices.instrument import Instrument
from sampletones_core.project.voices.sample import Sample
from sampletones_core.reconstructions import Reconstruction
from sampletones_core.reconstructions.reconstruction.stems.hearing import Hearing
from sampletones_core.reconstructions.reconstruction.stems.selection import StemSelection
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase
from tests.suite.stems import (
    SHARED_CHANNEL,
    SOLE_CHANNEL,
    STEM_A_ID,
    STEM_B_ID,
    everything_heard,
    single_entry_stems_data,
    taking_turns,
)

__all__ = ["taking_turns"]

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
    channel_name: ChannelName,
    instructions: Sequence[InstructionUnion],
    held_features: Iterable[FeatureKey],
) -> Reconstruction:
    """A one-channel reconstruction whose instrument leaves ``held_features`` to the channel."""
    instructions_list = list(instructions)
    reconstruction = Reconstruction.create(
        instructions={channel_name: instructions_list},
        config=Config(),
        coefficient=1.0,
        audio_filepath=(Path("/dev/null"),),
        stems_data=single_entry_stems_data(
            list(DEFAULT_CHANNELS),
            {channel_name: instructions_list},
        ),
    )
    reconstruction = reconstruction.with_channel_data(
        channel_name,
        list(instructions),
        reconstruction.initial_pitches[channel_name],
        held_features,
        heard=reconstruction.recorded_stem_ids,
    )
    return reconstruction


def _voice(
    channel_name: ChannelName,
    instructions: Sequence[InstructionUnion],
    held_features: Iterable[FeatureKey],
) -> VoiceReading:
    voice = Sample(name="lead", reconstruction=_reconstruction(channel_name, instructions, held_features))
    reading = VoiceReading.read(voice, channel_name)
    assert reading is not None
    return reading


def _channel_values() -> Dict[FeatureKey, int]:
    return CHANNEL_FEATURE_DEFAULTS.copy()


class TestAFrameSoundsAsTheInstrumentWroteIt(BaseTestSuite):
    """An instrument writing every dimension sounds its frames exactly as it holds them."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        channel_name: ChannelName
        instructions: List[InstructionUnion]

    test_cases = (
        TestCase(
            label="pulse",
            channel_name=ChannelName.PULSE1,
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
            channel_name=ChannelName.TRIANGLE,
            instructions=[TriangleInstruction(on=True, pitch=REFERENCE_PITCH)],
        ),
        TestCase(
            label="noise",
            channel_name=ChannelName.NOISE,
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
        voice = _voice(test_case.channel_name, test_case.instructions, ())

        assert voice.sound(test_case.instructions[0], _channel_values()) == test_case.instructions[0]

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_the_channel_takes_up_what_the_instrument_writes(self, test_case: TestCase) -> None:
        voice = _voice(test_case.channel_name, test_case.instructions, ())
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
        channel_name: ChannelName
        instruction: InstructionUnion
        held_feature: FeatureKey
        channel_value: int
        expected: InstructionUnion

    test_cases = (
        TestCase(
            label="pulse volume",
            channel_name=ChannelName.PULSE1,
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
            channel_name=ChannelName.PULSE1,
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
            channel_name=ChannelName.PULSE1,
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
            channel_name=ChannelName.TRIANGLE,
            instruction=TriangleInstruction(on=True, pitch=REFERENCE_PITCH),
            held_feature=FeatureKey.ARPEGGIO,
            channel_value=CHANNEL_ARPEGGIO,
            expected=TriangleInstruction(on=True, pitch=REFERENCE_PITCH + CHANNEL_ARPEGGIO),
        ),
        TestCase(
            label="noise period",
            channel_name=ChannelName.NOISE,
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
            channel_name=ChannelName.NOISE,
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
        voice = _voice(test_case.channel_name, [test_case.instruction], (test_case.held_feature,))
        values = _channel_values()
        values[test_case.held_feature] = test_case.channel_value

        assert voice.sound(test_case.instruction, values) == test_case.expected

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_a_held_dimension_leaves_the_channels_value_where_it_stands(self, test_case: TestCase) -> None:
        voice = _voice(test_case.channel_name, [test_case.instruction], (test_case.held_feature,))
        values = _channel_values()
        values[test_case.held_feature] = test_case.channel_value

        voice.sound(test_case.instruction, values)

        assert values[test_case.held_feature] == test_case.channel_value

    def test_an_instrument_holding_its_level_sounds_a_silent_frame(self) -> None:
        """Silence is stated by a volume envelope, so an instrument leaving one out plays on."""
        rest = PulseInstruction.null_instruction()
        voice = _voice(ChannelName.PULSE1, [self._INSTRUCTION, rest], (FeatureKey.VOLUME,))

        assert voice.sound(rest, _channel_values()).on is True

    def test_a_silent_frame_takes_the_channel_to_silence_where_the_instrument_writes_its_level(self) -> None:
        rest = PulseInstruction.null_instruction()
        voice = _voice(ChannelName.PULSE1, [self._INSTRUCTION, rest], ())
        values = _channel_values()

        assert voice.sound(rest, values).on is False
        assert values[FeatureKey.VOLUME] == 0

    def test_a_silent_frame_leaves_the_other_dimensions_where_the_channel_holds_them(self) -> None:
        rest = PulseInstruction.null_instruction()
        voice = _voice(ChannelName.PULSE1, [self._INSTRUCTION, rest], ())
        values = _channel_values()
        values[FeatureKey.DUTY_CYCLE] = DUTY_CYCLE

        voice.sound(rest, values)

        assert values[FeatureKey.DUTY_CYCLE] == DUTY_CYCLE


class TestHowLongAVoiceSoundsOnItsOwn:
    """A recording sounds the frames it holds, an instrument releasing at silence stops there, and any other
    instrument sounds until a row ends it."""

    def test_a_recording_sounds_the_frames_it_holds(self) -> None:
        reading = _voice(ChannelName.PULSE1, [PulseInstruction(on=True, pitch=60, volume=15, duty_cycle=0)] * 5, ())

        assert reading.length == 5

    def test_an_instrument_releasing_at_silence_sounds_up_to_its_release(self) -> None:
        reading = VoiceReading.read(_instrument_with_volume(Envelope[int](items=(15, 9, 0))), ChannelName.PULSE1)

        assert reading is not None
        assert reading.length == 3

    def test_an_instrument_circling_from_a_loop_point_sounds_until_a_row_ends_it(self) -> None:
        reading = VoiceReading.read(
            _instrument_with_volume(Envelope[int](items=(15, 9), loop_point=0)),
            ChannelName.PULSE1,
        )

        assert reading is not None
        assert reading.length is None


def _instrument_with_volume(volume: Envelope[int]) -> Instrument:
    return Instrument(name="lead", envelopes=InstrumentEnvelopes(volume=volume))


def _hearing(heard: Dict[ChannelName, FrozenSet[int]], channels_on: FrozenSet[ChannelName]) -> Hearing:
    return Hearing(selection=StemSelection(channels=heard), channels_on=channels_on)


def _whole(reconstruction: Reconstruction) -> Hearing:
    """Every recording heard on every channel the document plays, each of those kept on."""
    return Hearing(
        selection=everything_heard(reconstruction),
        channels_on=frozenset(reconstruction.playing_channels),
    )


class TestAKeyHearsWhatTheReaderHears:
    """A recording's readings follow the reader's hearing: recordings left out fall silent, channels off read nothing."""

    def test_a_recording_heard_whole_reads_as_its_own_frames(self, taking_turns: Reconstruction) -> None:
        sample = Sample(name="turns", reconstruction=taking_turns)

        readings = heard_readings(sample, _whole(taking_turns))

        for channel_name in (SHARED_CHANNEL, SOLE_CHANNEL):
            expected = VoiceReading.read(sample, channel_name)
            assert expected is not None
            assert list(readings[channel_name].instructions) == list(expected.instructions)
            assert readings[channel_name].reference == expected.reference

    def test_a_recording_left_out_reads_as_silence_where_it_held_frames(self, taking_turns: Reconstruction) -> None:
        sample = Sample(name="turns", reconstruction=taking_turns)
        hearing = _hearing(
            {SHARED_CHANNEL: frozenset({STEM_B_ID}), SOLE_CHANNEL: frozenset({STEM_B_ID})},
            frozenset({SHARED_CHANNEL, SOLE_CHANNEL}),
        )

        shared = heard_readings(sample, hearing)[SHARED_CHANNEL].instructions

        first, second = taking_turns.instructions[SHARED_CHANNEL]
        assert list(shared) == [type(first).null_instruction(), second]

    def test_a_channel_holding_no_frame_heard_reads_nothing(self, taking_turns: Reconstruction) -> None:
        sample = Sample(name="turns", reconstruction=taking_turns)
        hearing = _hearing(
            {SHARED_CHANNEL: frozenset({STEM_A_ID}), SOLE_CHANNEL: frozenset()},
            frozenset({SHARED_CHANNEL, SOLE_CHANNEL}),
        )

        readings = heard_readings(sample, hearing)

        assert SOLE_CHANNEL not in readings
        assert list(readings[SHARED_CHANNEL].instructions) == [taking_turns.instructions[SHARED_CHANNEL][0]]

    def test_a_channel_switched_off_reads_nothing(self, taking_turns: Reconstruction) -> None:
        sample = Sample(name="turns", reconstruction=taking_turns)
        whole = _whole(taking_turns)
        hearing = whole.model_copy(update={"channels_on": frozenset({SOLE_CHANNEL})})

        readings = heard_readings(sample, hearing)

        assert set(readings) == {SOLE_CHANNEL}
