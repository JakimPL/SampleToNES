from typing import Optional, Tuple

import numpy as np

from sampletones_core.constants.enums import ChannelName
from sampletones_core.constants.general import MAX_VOLUME
from sampletones_core.exporters import Features
from sampletones_core.features import RESTING_REFERENCE_PERIOD, RESTING_REFERENCE_PITCH
from sampletones_core.project.voices.creation import instrument_from_features, new_instrument
from sampletones_core.project.voices.loop import WHOLE_LOOP_POINT

TONAL_REFERENCE = 64
NOISE_REFERENCE = 5
VOLUME = (15, 12, 9)
ARPEGGIO = (0, 4, 7)
DUTY_CYCLE = (2, 2, 1)


def _features(
    reference: int,
    *,
    duty_cycle: Optional[Tuple[int, ...]] = DUTY_CYCLE,
    volume: Tuple[int, ...] = VOLUME,
) -> Features:
    """What one channel plays, as its exporter states it."""
    return Features(
        initial_pitch=reference,
        volume=np.array(volume, dtype=np.int8),
        arpeggio=np.array(ARPEGGIO, dtype=np.int8),
        pitch=None,
        hi_pitch=None,
        duty_cycle=None if duty_cycle is None else np.array(duty_cycle, dtype=np.int8),
    )


class TestNewInstrument:
    def test_a_new_instrument_sounds_a_frame_on_every_channel(self) -> None:
        instrument = new_instrument("lead")

        for channel_name in ChannelName.items():
            assert instrument.instructions(channel_name)

    def test_a_new_instrument_sounds_at_full_volume(self) -> None:
        instrument = new_instrument("lead")

        assert instrument.envelopes.volume == (MAX_VOLUME,)

    def test_a_new_instrument_repeats_its_envelopes_while_the_note_is_held(self) -> None:
        assert new_instrument("lead").loop_point == WHOLE_LOOP_POINT

    def test_a_new_instrument_leaves_the_arpeggio_and_the_duty_cycle_to_the_channel(self) -> None:
        instrument = new_instrument("lead")

        assert instrument.envelopes.arpeggio == ()
        assert instrument.envelopes.duty_cycle == ()

    def test_a_new_instrument_rests_where_a_channel_added_by_hand_rests(self) -> None:
        instrument = new_instrument("lead")

        assert instrument.root_pitch == RESTING_REFERENCE_PITCH
        assert instrument.root_period == RESTING_REFERENCE_PERIOD

    def test_each_new_instrument_is_a_voice_of_its_own(self) -> None:
        assert new_instrument("lead").id != new_instrument("lead").id


class TestAnInstrumentTakenFromAChannel:
    """A recording's channel is read back as envelopes, so what it played becomes editable."""

    def test_the_envelopes_come_across_as_the_channel_played_them(self) -> None:
        instrument = instrument_from_features(
            "Bass (pulse1)",
            _features(TONAL_REFERENCE),
            ChannelName.PULSE1,
            loop_point=None,
        )

        assert instrument.envelopes.volume == VOLUME
        assert instrument.envelopes.arpeggio == ARPEGGIO
        assert instrument.envelopes.duty_cycle == DUTY_CYCLE

    def test_a_dimension_the_channel_governs_stays_the_channels(self) -> None:
        """An empty envelope means the channel keeps the value it holds, on either side of this."""
        instrument = instrument_from_features(
            "Bass (pulse1)",
            _features(TONAL_REFERENCE, volume=()),
            ChannelName.PULSE1,
            loop_point=None,
        )

        assert instrument.envelopes.volume == ()

    def test_a_dimension_the_channel_lacks_is_left_unwritten(self) -> None:
        """The triangle channel offers no duty cycle, so the voice writes none for it."""
        instrument = instrument_from_features(
            "Bass (triangle)",
            _features(TONAL_REFERENCE, duty_cycle=None),
            ChannelName.TRIANGLE,
            loop_point=None,
        )

        assert instrument.envelopes.duty_cycle == ()

    def test_a_tonal_channels_reference_becomes_the_note_the_arpeggio_is_measured_against(self) -> None:
        instrument = instrument_from_features(
            "Bass (pulse1)",
            _features(TONAL_REFERENCE),
            ChannelName.PULSE1,
            loop_point=None,
        )

        assert instrument.root_pitch == TONAL_REFERENCE
        assert instrument.root_period == RESTING_REFERENCE_PERIOD

    def test_the_noise_channels_reference_becomes_the_period_the_arpeggio_is_measured_against(self) -> None:
        instrument = instrument_from_features(
            "Bass (noise)",
            _features(NOISE_REFERENCE),
            ChannelName.NOISE,
            loop_point=None,
        )

        assert instrument.root_period == NOISE_REFERENCE
        assert instrument.root_pitch == RESTING_REFERENCE_PITCH

    def test_the_voice_reads_on_its_own_channel_what_that_channel_stated(self) -> None:
        """The reference travels with the envelopes, so the two agree where they came from."""
        features = _features(TONAL_REFERENCE)

        instrument = instrument_from_features("Bass (pulse1)", features, ChannelName.PULSE1, loop_point=None)

        assert instrument.features(ChannelName.PULSE1).initial_pitch == features.initial_pitch

    def test_the_voice_sounds_the_frames_the_channel_sounded(self) -> None:
        instrument = instrument_from_features(
            "Bass (pulse1)",
            _features(TONAL_REFERENCE),
            ChannelName.PULSE1,
            loop_point=None,
        )

        assert len(instrument.instructions(ChannelName.PULSE1)) == len(VOLUME)

    def test_the_voice_repeats_from_the_tick_it_was_given(self) -> None:
        instrument = instrument_from_features(
            "Bass (pulse1)",
            _features(TONAL_REFERENCE),
            ChannelName.PULSE1,
            loop_point=WHOLE_LOOP_POINT,
        )

        assert instrument.loop_point == WHOLE_LOOP_POINT

    def test_the_voice_carries_the_name_it_was_given(self) -> None:
        instrument = instrument_from_features(
            "Bass (pulse1)",
            _features(TONAL_REFERENCE),
            ChannelName.PULSE1,
            loop_point=None,
        )

        assert instrument.name == "Bass (pulse1)"
