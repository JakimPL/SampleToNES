from typing import Dict, Final, FrozenSet, List, Tuple

import numpy as np

from sampletones_core.audio.mixing import align, mix
from sampletones_core.constants.algorithm import AUTHORED_STEM_ID, RESTING_STEM_ID
from sampletones_core.constants.enums import ChannelName, bending_channels
from sampletones_core.instructions import PulseInstruction
from sampletones_core.reconstructions import Reconstruction
from sampletones_core.reconstructions.reconstruction.renders import rendered_channels, rendered_mix
from sampletones_core.reconstructions.reconstruction.stems.channel_assignment import ChannelAssignment
from sampletones_core.reconstructions.reconstruction.stems.data import StemsData
from sampletones_core.reconstructions.reconstruction.stems.hearing import (
    Hearing,
    carried_channels_on,
    carried_heard,
    carried_hearing,
    heard_by_stem,
    heard_renders,
    hearing_carried_onto,
    offered_channels,
    selection_of,
    whole_hearing,
)
from sampletones_core.reconstructions.reconstruction.stems.selection import StemSelection
from sampletones_core.reconstructions.reconstructor.stems.configs.config import StemsConfig
from sampletones_core.reconstructions.reconstructor.stems.configs.entry import StemEntry
from sampletones_core.reconstructions.reconstructor.stems.configs.hierarchy import StemsHierarchy
from sampletones_core.reconstructions.reconstructor.stems.configs.settings import StemSettings
from tests.suite.sequencer import sample_reconstruction
from tests.suite.stems import (
    RECORDED_SCALE,
    SHARED_CHANNEL,
    SOLE_CHANNEL,
    STEM_A_ID,
    STEM_B_ID,
    TAKING_TURNS_DUTY_CYCLE,
    TAKING_TURNS_PITCH,
    TAKING_TURNS_VOLUME,
    taking_turns,
)

__all__ = ["taking_turns"]

EVERY_CHANNEL: Final[FrozenSet[ChannelName]] = frozenset(ChannelName.items())
CHANNEL: Final[ChannelName] = ChannelName.PULSE1
OTHER_CHANNEL: Final[ChannelName] = ChannelName.TRIANGLE
STEM_A: Final[int] = 0
STEM_B: Final[int] = 1
BOTH: Final[FrozenSet[int]] = frozenset({STEM_A, STEM_B})
NOTHING_OFFERED: Final[Dict[int, FrozenSet[ChannelName]]] = {}


def _stems_data(*stem_lists: Tuple[ChannelName, List[int]]) -> StemsData:
    entries = [
        StemEntry(
            id=stem_id,
            settings=StemSettings(channels=[CHANNEL], bends=bending_channels([CHANNEL])),
        )
        for stem_id in range(3)
    ]
    return StemsData(
        config=StemsConfig(
            entries=entries,
            hierarchy=StemsHierarchy(levels=[[entry.id] for entry in entries]),
        ),
        assignments=[ChannelAssignment(channel_name=channel, stem_ids=stem_ids) for channel, stem_ids in stem_lists],
        scale=RECORDED_SCALE,
    )


def _hearing(stem_ids: FrozenSet[int], channels_on: FrozenSet[ChannelName] = EVERY_CHANNEL) -> Hearing:
    return Hearing(selection=StemSelection.everywhere(stem_ids, ChannelName.items()), channels_on=channels_on)


def _held_on(*channels: ChannelName) -> Dict[int, FrozenSet[ChannelName]]:
    """What a record offers where both recordings hold frames on every channel given."""
    return offered_channels(_stems_data(*((channel, [STEM_A, STEM_B]) for channel in channels)))


def _with_a_frame_of_the_readers_own(reconstruction: Reconstruction) -> Reconstruction:
    """The document with one frame past the end of its shared channel written by the reader."""
    instruction = PulseInstruction(
        on=True,
        pitch=TAKING_TURNS_PITCH,
        volume=TAKING_TURNS_VOLUME,
        duty_cycle=TAKING_TURNS_DUTY_CYCLE,
    )
    return reconstruction.with_channel_data(
        SHARED_CHANNEL,
        [instruction] * (len(reconstruction.instructions[SHARED_CHANNEL]) + 1),
        TAKING_TURNS_PITCH,
        (),
        heard=reconstruction.recorded_stem_ids,
    )


class TestWhatARecordingOffers:
    def test_a_recording_offers_the_channels_it_holds_frames_on(self) -> None:
        stems_data = _stems_data((CHANNEL, [STEM_A, STEM_B]), (OTHER_CHANNEL, [STEM_A, RESTING_STEM_ID]))

        offered = offered_channels(stems_data)

        assert offered[STEM_A] == frozenset({CHANNEL, OTHER_CHANNEL})
        assert offered[STEM_B] == frozenset({CHANNEL})

    def test_a_recording_holding_nothing_offers_nothing(self) -> None:
        stems_data = _stems_data((CHANNEL, [STEM_A]))

        assert offered_channels(stems_data)[STEM_B] == frozenset()

    def test_the_frames_the_reader_wrote_offer_a_row_of_their_own(self) -> None:
        stems_data = _stems_data((CHANNEL, [STEM_A, AUTHORED_STEM_ID]))

        assert offered_channels(stems_data)[AUTHORED_STEM_ID] == frozenset({CHANNEL})


class TestHowAChoiceTravelsAcrossAnEdit:
    """One rule carries the reader's choice onto a new record, read by the worker and by the listening state alike."""

    def test_a_channel_a_recording_keeps_holding_keeps_the_readers_choice(self) -> None:
        heard = {STEM_A: frozenset({CHANNEL}), STEM_B: frozenset({CHANNEL, OTHER_CHANNEL})}

        carried = carried_heard(heard, _held_on(CHANNEL, OTHER_CHANNEL), _held_on(CHANNEL, OTHER_CHANNEL))

        assert carried[STEM_A] == heard[STEM_A]
        assert carried[STEM_B] == heard[STEM_B]

    def test_a_channel_a_recording_newly_reaches_joins_what_is_heard(self) -> None:
        heard = {STEM_A: frozenset({CHANNEL}), STEM_B: frozenset()}

        carried = carried_heard(heard, _held_on(CHANNEL), _held_on(CHANNEL, OTHER_CHANNEL))

        assert carried[STEM_A] == frozenset({CHANNEL, OTHER_CHANNEL})
        assert carried[STEM_B] == frozenset({OTHER_CHANNEL})

    def test_a_channel_a_recording_stops_holding_leaves_what_is_heard(self) -> None:
        heard = _held_on(CHANNEL, OTHER_CHANNEL)

        carried = carried_heard(heard, _held_on(CHANNEL, OTHER_CHANNEL), _held_on(CHANNEL))

        assert carried == _held_on(CHANNEL)

    def test_a_recording_leaving_the_record_leaves_the_choice(self) -> None:
        heard = {STEM_A: frozenset({CHANNEL}), STEM_B: frozenset({CHANNEL})}
        offered_after = {STEM_A: frozenset({CHANNEL})}

        carried = carried_heard(heard, _held_on(CHANNEL), offered_after)

        assert carried == offered_after

    def test_the_readers_own_row_joins_what_is_heard_where_it_first_appears(self) -> None:
        heard = {STEM_A: frozenset({CHANNEL}), STEM_B: frozenset()}
        offered_after = offered_channels(_stems_data((CHANNEL, [STEM_A, STEM_B, AUTHORED_STEM_ID])))

        carried = carried_heard(heard, _held_on(CHANNEL), offered_after)

        assert carried[AUTHORED_STEM_ID] == frozenset({CHANNEL})
        assert carried[STEM_B] == frozenset()

    def test_a_record_offering_nothing_before_hears_everything_after(self) -> None:
        offered_after = _held_on(CHANNEL, OTHER_CHANNEL)

        assert carried_heard({}, NOTHING_OFFERED, offered_after) == offered_after

    def test_a_channel_coming_into_play_joins_the_channels_on(self) -> None:
        carried = carried_channels_on(frozenset(), frozenset({CHANNEL}), frozenset({CHANNEL, SOLE_CHANNEL}))

        assert carried == frozenset({SOLE_CHANNEL})

    def test_a_channel_switched_off_stays_off_and_one_leaving_play_leaves(self) -> None:
        both = frozenset({CHANNEL, SOLE_CHANNEL})

        assert carried_channels_on(frozenset({CHANNEL}), both, both) == frozenset({CHANNEL})
        assert carried_channels_on(both, both, frozenset({CHANNEL})) == frozenset({CHANNEL})

    def test_a_hearing_is_carried_on_both_of_its_choices(self) -> None:
        hearing = Hearing(
            selection=StemSelection.everywhere(frozenset({STEM_A}), [CHANNEL]),
            channels_on=frozenset({CHANNEL}),
        )

        carried = carried_hearing(
            hearing,
            offered_before=_held_on(CHANNEL),
            playing_before=frozenset({CHANNEL}),
            offered_after=offered_channels(_stems_data((CHANNEL, [STEM_A, STEM_B, AUTHORED_STEM_ID]))),
            playing_after=frozenset({CHANNEL, SOLE_CHANNEL}),
        )

        assert carried.selection.stems_for(CHANNEL) == frozenset({STEM_A, AUTHORED_STEM_ID})
        assert carried.channels_on == frozenset({CHANNEL, SOLE_CHANNEL})

    def test_a_selection_turned_around_and_back_is_itself(self) -> None:
        heard = {STEM_A: frozenset({CHANNEL}), STEM_B: frozenset({CHANNEL, OTHER_CHANNEL})}

        selection = selection_of(heard)

        assert selection.channels.keys() == set(ChannelName.items())
        assert selection.stems_for(CHANNEL) == BOTH
        assert selection.stems_for(ChannelName.NOISE) == frozenset()
        assert selection_of(heard_by_stem(selection, _held_on(CHANNEL, OTHER_CHANNEL))) == selection

    def test_an_edit_writing_frames_of_the_readers_own_hears_them(self, taking_turns: Reconstruction) -> None:
        """The worker hears the document it rebuilt as the listening will, so its reading keys the cache alike."""
        edited = _with_a_frame_of_the_readers_own(taking_turns)

        carried = hearing_carried_onto(_hearing(taking_turns.recorded_stem_ids), taking_turns, edited)

        assert AUTHORED_STEM_ID in carried.selection.stems_for(SHARED_CHANNEL)
        assert carried.filter_for(SHARED_CHANNEL, edited.stems_data) is None
        assert carried.channels_on == frozenset(edited.playing_channels)


class TestWhatAWholeHearingHears:
    """A document heard whole hears every owner on every channel and keeps every playing channel on."""

    def test_every_channel_is_heard_whole(self, taking_turns: Reconstruction) -> None:
        hearing = whole_hearing(taking_turns)

        assert all(hearing.filter_for(channel, taking_turns.stems_data) is None for channel in ChannelName.items())
        assert hearing.channels_on == frozenset(taking_turns.playing_channels)

    def test_the_readers_own_row_is_heard_too(self, taking_turns: Reconstruction) -> None:
        edited = _with_a_frame_of_the_readers_own(taking_turns)

        hearing = whole_hearing(edited)

        assert AUTHORED_STEM_ID in hearing.selection.stems_for(SHARED_CHANNEL)
        assert hearing.filter_for(SHARED_CHANNEL, edited.stems_data) is None


class TestWhatAChannelIsFilteredBy:
    """A channel's filter names the owners heard, so two hearings reaching the channel alike read it alike."""

    def test_every_owner_heard_is_heard_whole(self) -> None:
        stems_data = _stems_data((CHANNEL, [0, 1, RESTING_STEM_ID]))

        assert _hearing(frozenset({0, 1})).filter_for(CHANNEL, stems_data) is None

    def test_an_owner_left_out_names_the_owners_heard(self) -> None:
        stems_data = _stems_data((CHANNEL, [0, 1]))

        assert _hearing(frozenset({0})).filter_for(CHANNEL, stems_data) == frozenset({0})

    def test_recordings_beyond_the_channel_are_left_out_of_the_name(self) -> None:
        stems_data = _stems_data((CHANNEL, [0, 1]))

        assert _hearing(frozenset({0, 2})).filter_for(CHANNEL, stems_data) == frozenset({0})
        assert _hearing(frozenset({0, 1, 2})).filter_for(CHANNEL, stems_data) is None

    def test_the_readers_own_row_counts_as_an_owner(self) -> None:
        stems_data = _stems_data((CHANNEL, [0, AUTHORED_STEM_ID]))

        assert _hearing(frozenset({0})).filter_for(CHANNEL, stems_data) == frozenset({0})
        assert _hearing(frozenset({0, AUTHORED_STEM_ID})).filter_for(CHANNEL, stems_data) is None

    def test_a_channel_the_record_leaves_out_is_heard_whole(self) -> None:
        stems_data = _stems_data((CHANNEL, [0]))

        assert _hearing(frozenset()).filter_for(ChannelName.NOISE, stems_data) is None


class TestWhatAHearingSounds:
    """The heard mix and what plays, read from the channels' renders: the arrays handed in come back by
    identity where nothing is filtered, and a narrower choice is summed in channel order.
    """

    def test_heard_whole_and_every_channel_on_sounds_the_mix_itself(self, taking_turns) -> None:
        channels = rendered_channels(taking_turns)
        mixed = rendered_mix(taking_turns)

        heard = heard_renders(taking_turns, _hearing(taking_turns.recorded_stem_ids), channels, mixed)

        assert heard.mix is mixed
        assert heard.playing is mixed

    def test_a_recording_left_out_is_silenced_in_the_mix(self, taking_turns) -> None:
        channels = rendered_channels(taking_turns)
        mixed = rendered_mix(taking_turns)

        heard = heard_renders(taking_turns, _hearing(frozenset({STEM_A_ID})), channels, mixed)

        assert heard.mix is not mixed
        assert np.any(heard.mix != mixed)
        assert heard.playing is heard.mix

    def test_a_channel_switched_off_plays_the_rest(self, taking_turns) -> None:
        channels = rendered_channels(taking_turns)
        mixed = rendered_mix(taking_turns)

        heard = heard_renders(
            taking_turns,
            _hearing(taking_turns.recorded_stem_ids, frozenset({SOLE_CHANNEL})),
            channels,
            mixed,
        )

        assert heard.mix is mixed
        np.testing.assert_array_equal(heard.playing, align([channels[SOLE_CHANNEL]], len(mixed))[0])
        assert len(heard.playing) == len(mixed)

    def test_two_of_three_channels_on_are_summed_in_channel_order(self) -> None:
        document = sample_reconstruction([ChannelName.PULSE1, ChannelName.TRIANGLE, ChannelName.NOISE])
        channels = rendered_channels(document)
        mixed = rendered_mix(document)

        heard = heard_renders(
            document,
            _hearing(document.recorded_stem_ids, frozenset({ChannelName.TRIANGLE, ChannelName.PULSE1})),
            channels,
            mixed,
        )

        assert heard.mix is mixed
        np.testing.assert_array_equal(
            heard.playing,
            mix(align([channels[ChannelName.PULSE1], channels[ChannelName.TRIANGLE]], len(mixed))),
        )

    def test_every_channel_switched_off_plays_silence(self, taking_turns) -> None:
        channels = rendered_channels(taking_turns)
        mixed = rendered_mix(taking_turns)

        heard = heard_renders(taking_turns, _hearing(taking_turns.recorded_stem_ids, frozenset()), channels, mixed)

        np.testing.assert_array_equal(heard.playing, np.zeros_like(mixed))
        assert len(heard.playing) == len(mixed)

    def test_channels_switched_off_beyond_play_change_nothing(self, taking_turns) -> None:
        channels = rendered_channels(taking_turns)
        mixed = rendered_mix(taking_turns)
        on = frozenset({SHARED_CHANNEL, SOLE_CHANNEL, ChannelName.NOISE})

        heard = heard_renders(taking_turns, _hearing(taking_turns.recorded_stem_ids, on), channels, mixed)

        assert heard.playing is mixed
        assert STEM_B_ID in taking_turns.recorded_stem_ids
