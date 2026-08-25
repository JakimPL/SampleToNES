from typing import Final

import numpy as np
import pytest

from sampletones_core.configs import Config
from sampletones_core.constants.enums import ChannelName
from sampletones_core.features.envelope import Envelope
from sampletones_core.performance.audition import (
    audition_audio,
    audition_instructions,
    audition_ticks,
)
from sampletones_core.project.voices.envelopes import InstrumentEnvelopes
from sampletones_core.project.voices.instrument import Instrument

REFERENCE_PITCH: Final[int] = 60
REFERENCE_PERIOD: Final[int] = 8
TYPED_PITCH: Final[int] = 67
NES_FREQUENCY: Final[int] = 60
SAMPLE_RATE: Final[int] = 44100
WRITTEN_TICKS: Final[int] = 3
CAP: Final[int] = 24


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
            ticks=WRITTEN_TICKS,
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
            ticks=WRITTEN_TICKS,
        )

        assert instructions == instrument.instructions(ChannelName.PULSE1)

    def test_a_voice_sounds_at_full_volume_however_loud_its_envelope_is(self) -> None:
        instructions = audition_instructions(
            _instrument(),
            ChannelName.PULSE1,
            pitch=TYPED_PITCH,
            ticks=WRITTEN_TICKS,
        )

        assert [instruction.volume for instruction in instructions] == [15, 12, 9]

    def test_the_noise_channel_walks_the_periods_its_arpeggio_names(self) -> None:
        instructions = audition_instructions(
            _instrument(),
            ChannelName.NOISE,
            pitch=REFERENCE_PERIOD,
            ticks=WRITTEN_TICKS,
        )

        assert [instruction.period for instruction in instructions] == [8, 12, 15]

    def test_a_channel_reads_the_dimensions_its_generator_offers(self) -> None:
        instructions = audition_instructions(
            _instrument(),
            ChannelName.TRIANGLE,
            pitch=TYPED_PITCH,
            ticks=WRITTEN_TICKS,
        )

        assert all(instruction.on for instruction in instructions)


class TestHowLongAnAuditionSounds:
    """A voice sounded on its own runs to the release it states, or to the length it is offered."""

    def test_a_voice_whose_volume_ends_in_silence_stops_where_it_releases(self) -> None:
        """The dimension holds its last item forever, so a final zero is where the note ends."""
        instrument = Instrument(
            name="decay",
            envelopes=InstrumentEnvelopes(volume=Envelope[int](items=(15, 9, 3, 0))),
        )

        assert audition_ticks(instrument, cap=CAP) == 4

    def test_a_voice_that_sustains_sounds_for_the_length_it_is_offered(self) -> None:
        """A dimension circling from a loop point never reaches a last item, so nothing ends it."""
        instrument = Instrument(
            name="sustain",
            envelopes=InstrumentEnvelopes(volume=Envelope[int](items=(15,), loop_point=0)),
        )

        assert audition_ticks(instrument, cap=CAP) == CAP

    def test_a_volume_circling_back_through_silence_still_sounds_on(self) -> None:
        """A zero the dimension loops past is a silent tick, and the note goes on past it."""
        instrument = Instrument(
            name="pulsing",
            envelopes=InstrumentEnvelopes(volume=Envelope[int](items=(15, 0), loop_point=0)),
        )

        assert audition_ticks(instrument, cap=CAP) == CAP

    def test_a_voice_leaving_its_volume_to_the_channel_sounds_for_the_length_offered(self) -> None:
        instrument = Instrument(
            name="held",
            envelopes=InstrumentEnvelopes(arpeggio=Envelope[int](items=(0, 4))),
        )

        assert audition_ticks(instrument, cap=CAP) == CAP


class TestTheFramesAnAuditionSoundsPastWhatIsWritten:
    """A voice sounds past its written frames the way a held tracker row sounds it."""

    def test_a_dimension_holds_its_last_item_once_the_written_frames_run_out(self) -> None:
        instrument = _instrument()

        instructions = audition_instructions(
            instrument,
            ChannelName.PULSE1,
            pitch=REFERENCE_PITCH,
            ticks=WRITTEN_TICKS + 2,
        )

        assert [instruction.volume for instruction in instructions] == [15, 12, 9, 9, 9]

    def test_a_dimension_circles_from_the_item_it_repeats_from(self) -> None:
        instrument = Instrument(
            name="looping",
            envelopes=InstrumentEnvelopes(volume=Envelope[int](items=(15, 12, 9), loop_point=1)),
        )

        instructions = audition_instructions(
            instrument,
            ChannelName.PULSE1,
            pitch=REFERENCE_PITCH,
            ticks=6,
        )

        assert [instruction.volume for instruction in instructions] == [15, 12, 9, 12, 9, 12]


class TestTheAudioAnAuditionPlays:
    @pytest.mark.parametrize(
        "channel_name",
        list(ChannelName.items()),
        ids=[channel_name.value for channel_name in ChannelName.items()],
    )
    def test_a_voice_renders_one_frame_per_tick_it_is_sounded_for(
        self,
        channel_name: ChannelName,
    ) -> None:
        config = _config()
        audio = audition_audio(
            _instrument(),
            channel_name,
            config,
            pitch=TYPED_PITCH,
            ticks=CAP,
        )

        assert audio is not None
        assert audio.shape == (CAP * config.frame_length,)

    def test_a_voice_writing_no_envelope_sounds_nothing(self) -> None:
        assert (
            audition_audio(
                Instrument(name="silent"),
                ChannelName.PULSE1,
                _config(),
                pitch=TYPED_PITCH,
                ticks=CAP,
            )
            is None
        )

    def test_two_notes_of_one_voice_render_to_different_audio(self) -> None:
        config = _config()
        instrument = _instrument()
        low = audition_audio(
            instrument,
            ChannelName.PULSE1,
            config,
            pitch=REFERENCE_PITCH,
            ticks=WRITTEN_TICKS,
        )
        high = audition_audio(
            instrument,
            ChannelName.PULSE1,
            config,
            pitch=TYPED_PITCH,
            ticks=WRITTEN_TICKS,
        )

        assert low is not None and high is not None
        assert not np.array_equal(low, high)
