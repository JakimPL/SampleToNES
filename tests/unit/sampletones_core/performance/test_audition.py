from typing import Final

import numpy as np
import pytest

from sampletones_core.configs import Config
from sampletones_core.constants.enums import ChannelName
from sampletones_core.features.envelope import Envelope
from sampletones_core.performance.audition import audition_audio, audition_instructions
from sampletones_core.project.voices.envelopes import InstrumentEnvelopes
from sampletones_core.project.voices.instrument import Instrument

REFERENCE_PITCH: Final[int] = 60
REFERENCE_PERIOD: Final[int] = 8
TYPED_PITCH: Final[int] = 67
NES_FREQUENCY: Final[int] = 60
SAMPLE_RATE: Final[int] = 44100


def _instrument() -> Instrument:
    """A voice with a value in every dimension, so each one shows in the frames it makes."""
    return Instrument(
        name="lead",
        envelopes=InstrumentEnvelopes(
            volume=Envelope[int](items=(15, 12, 9)),
            arpeggio=Envelope[int](items=(0, 4, 7)),
            duty_cycle=Envelope[int](items=(2,)),
        ),
        initial_pitch=REFERENCE_PITCH,
        initial_period=REFERENCE_PERIOD,
    )


def _config() -> Config:
    return Config().with_library(
        nes_frequency=NES_FREQUENCY,
        sample_rate=SAMPLE_RATE,
    )


class TestTheNoteAnAuditionSounds:
    def test_the_reference_cancels_so_a_voice_sounds_at_the_note_asked_for(self) -> None:
        instructions = audition_instructions(
            _instrument(),
            ChannelName.PULSE1,
            pitch=TYPED_PITCH,
        )

        assert [instruction.pitch for instruction in instructions] == [
            TYPED_PITCH,
            TYPED_PITCH + 4,
            TYPED_PITCH + 7,
        ]

    def test_sounding_at_its_own_reference_leaves_the_frames_as_they_stand(self) -> None:
        instrument = _instrument()
        instructions = audition_instructions(
            instrument,
            ChannelName.PULSE1,
            pitch=REFERENCE_PITCH,
        )

        assert instructions == instrument.instructions(ChannelName.PULSE1)

    def test_a_voice_sounds_at_full_volume_however_loud_its_envelope_is(self) -> None:
        instructions = audition_instructions(
            _instrument(),
            ChannelName.PULSE1,
            pitch=TYPED_PITCH,
        )

        assert [instruction.volume for instruction in instructions] == [15, 12, 9]

    def test_the_noise_channel_walks_the_periods_its_arpeggio_names(self) -> None:
        instructions = audition_instructions(
            _instrument(),
            ChannelName.NOISE,
            pitch=REFERENCE_PERIOD,
        )

        assert [instruction.period for instruction in instructions] == [8, 12, 15]

    def test_a_channel_reads_the_dimensions_its_generator_offers(self) -> None:
        instructions = audition_instructions(
            _instrument(),
            ChannelName.TRIANGLE,
            pitch=TYPED_PITCH,
        )

        assert all(instruction.on for instruction in instructions)


class TestTheAudioAnAuditionPlays:
    @pytest.mark.parametrize(
        "channel_name",
        list(ChannelName.items()),
        ids=[channel_name.value for channel_name in ChannelName.items()],
    )
    def test_a_voice_renders_one_frame_per_tick_of_its_envelopes(
        self,
        channel_name: ChannelName,
    ) -> None:
        config = _config()
        audio = audition_audio(
            _instrument(),
            channel_name,
            config,
            pitch=TYPED_PITCH,
        )

        assert audio is not None
        assert audio.shape == (3 * config.frame_length,)

    def test_a_voice_writing_no_envelope_sounds_nothing(self) -> None:
        assert (
            audition_audio(
                Instrument(name="silent"),
                ChannelName.PULSE1,
                _config(),
                pitch=TYPED_PITCH,
            )
            is None
        )

    def test_two_notes_of_one_voice_render_to_different_audio(self) -> None:
        config = _config()
        instrument = _instrument()
        low = audition_audio(instrument, ChannelName.PULSE1, config, pitch=REFERENCE_PITCH)
        high = audition_audio(instrument, ChannelName.PULSE1, config, pitch=TYPED_PITCH)

        assert low is not None and high is not None
        assert not np.array_equal(low, high)
