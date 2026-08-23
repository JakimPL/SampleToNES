from sampletones_core.constants.enums import ChannelName
from sampletones_core.constants.general import MAX_VOLUME
from sampletones_core.features import RESTING_REFERENCE_PERIOD, RESTING_REFERENCE_PITCH
from sampletones_core.project.voices.creation import new_instrument
from sampletones_core.project.voices.loop import WHOLE_LOOP_POINT


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
