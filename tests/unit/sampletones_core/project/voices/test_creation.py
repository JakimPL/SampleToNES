from sampletones_core.constants.enums import ChannelName
from sampletones_core.constants.general import MAX_VOLUME
from sampletones_core.features import RESTING_REFERENCE_PERIOD, RESTING_REFERENCE_PITCH
from sampletones_core.project.voices.creation import new_shape
from sampletones_core.project.voices.loop import WHOLE_LOOP_POINT


class TestNewShape:
    def test_a_new_shape_sounds_a_frame_on_every_channel(self) -> None:
        shape = new_shape("lead")

        for channel_name in ChannelName.items():
            assert shape.instructions(channel_name)

    def test_a_new_shape_sounds_at_full_volume(self) -> None:
        shape = new_shape("lead")

        assert shape.envelopes.volume == (MAX_VOLUME,)

    def test_a_new_shape_repeats_its_envelopes_while_the_note_is_held(self) -> None:
        assert new_shape("lead").loop_point == WHOLE_LOOP_POINT

    def test_a_new_shape_leaves_the_arpeggio_and_the_duty_cycle_to_the_channel(self) -> None:
        shape = new_shape("lead")

        assert shape.envelopes.arpeggio == ()
        assert shape.envelopes.duty_cycle == ()

    def test_a_new_shape_rests_where_a_channel_added_by_hand_rests(self) -> None:
        shape = new_shape("lead")

        assert shape.root_pitch == RESTING_REFERENCE_PITCH
        assert shape.root_period == RESTING_REFERENCE_PERIOD

    def test_each_new_shape_is_a_voice_of_its_own(self) -> None:
        assert new_shape("lead").id != new_shape("lead").id
