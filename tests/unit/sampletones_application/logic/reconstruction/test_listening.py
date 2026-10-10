from typing import Final, FrozenSet, List

import pytest

from sampletones_application.logic.reconstruction.listening import Listening, offered_channels
from sampletones_core.constants.algorithm import AUTHORED_STEM_ID, RESTING_STEM_ID
from sampletones_core.constants.enums import ChannelName, bending_channels
from sampletones_core.reconstructions.reconstruction.stems.channel_assignment import ChannelAssignment
from sampletones_core.reconstructions.reconstruction.stems.data import StemsData
from sampletones_core.reconstructions.reconstructor.stems.configs.config import StemsConfig
from sampletones_core.reconstructions.reconstructor.stems.configs.entry import StemEntry
from sampletones_core.reconstructions.reconstructor.stems.configs.hierarchy import StemsHierarchy
from sampletones_core.reconstructions.reconstructor.stems.configs.settings import StemSettings
from tests.suite.stems import RECORDED_SCALE

STEM_A: Final[int] = 0
STEM_B: Final[int] = 1
STEM_CHANNELS: Final[List[ChannelName]] = [ChannelName.PULSE1, ChannelName.TRIANGLE]
EVERY_CHANNEL: Final[FrozenSet[ChannelName]] = frozenset(ChannelName.items())
PULSES: Final[FrozenSet[ChannelName]] = frozenset({ChannelName.PULSE1, ChannelName.PULSE2})


def _stems_data(*assignments: ChannelAssignment) -> StemsData:
    entries = [
        StemEntry(
            id=stem_id,
            settings=StemSettings(channels=STEM_CHANNELS, bends=bending_channels(STEM_CHANNELS)),
        )
        for stem_id in (STEM_A, STEM_B)
    ]
    return StemsData(
        config=StemsConfig(
            entries=entries,
            hierarchy=StemsHierarchy(levels=[[STEM_A, STEM_B]]),
        ),
        assignments=list(assignments),
        scale=RECORDED_SCALE,
    )


@pytest.fixture
def listening() -> Listening:
    return Listening()


class TestWhatARecordingOffers:
    def test_a_recording_offers_the_channels_it_holds_frames_on(self) -> None:
        stems_data = _stems_data(
            ChannelAssignment(channel_name=ChannelName.PULSE1, stem_ids=[STEM_A, STEM_B]),
            ChannelAssignment(channel_name=ChannelName.TRIANGLE, stem_ids=[STEM_A, RESTING_STEM_ID]),
        )

        offered = offered_channels(stems_data)

        assert offered[STEM_A] == frozenset({ChannelName.PULSE1, ChannelName.TRIANGLE})
        assert offered[STEM_B] == frozenset({ChannelName.PULSE1})

    def test_a_recording_holding_nothing_offers_nothing(self) -> None:
        stems_data = _stems_data(ChannelAssignment(channel_name=ChannelName.PULSE1, stem_ids=[STEM_A]))

        assert offered_channels(stems_data)[STEM_B] == frozenset()

    def test_the_frames_the_reader_wrote_offer_a_row_of_their_own(self) -> None:
        stems_data = _stems_data(
            ChannelAssignment(channel_name=ChannelName.PULSE1, stem_ids=[STEM_A, AUTHORED_STEM_ID]),
        )

        assert offered_channels(stems_data)[AUTHORED_STEM_ID] == frozenset({ChannelName.PULSE1})


class TestWhatAFreshDocumentIsHeardAs:
    def test_every_recording_is_heard_everywhere_it_holds_frames(self, listening: Listening) -> None:
        stems_data = _stems_data(
            ChannelAssignment(channel_name=ChannelName.PULSE1, stem_ids=[STEM_A, STEM_B]),
            ChannelAssignment(channel_name=ChannelName.TRIANGLE, stem_ids=[STEM_A, RESTING_STEM_ID]),
        )

        listening.adopt(stems_data, EVERY_CHANNEL)

        assert listening.heard == listening.offered

    def test_the_selection_answers_each_channel_with_the_recordings_on_it(self, listening: Listening) -> None:
        stems_data = _stems_data(
            ChannelAssignment(channel_name=ChannelName.PULSE1, stem_ids=[STEM_A, STEM_B]),
            ChannelAssignment(channel_name=ChannelName.TRIANGLE, stem_ids=[STEM_A, RESTING_STEM_ID]),
        )

        listening.adopt(stems_data, EVERY_CHANNEL)

        assert listening.heard_on(ChannelName.PULSE1) == frozenset({STEM_A, STEM_B})
        assert listening.heard_on(ChannelName.TRIANGLE) == frozenset({STEM_A})
        assert listening.heard_on(ChannelName.NOISE) == frozenset()


class TestWhatTheChoiceCarriesAcrossAnEdit:
    """A choice the reader made survives the next reading of the record."""

    @staticmethod
    def _held_on(*channels: ChannelName) -> StemsData:
        return _stems_data(
            *(ChannelAssignment(channel_name=channel_name, stem_ids=[STEM_A, STEM_B]) for channel_name in channels)
        )

    def test_a_channel_a_recording_keeps_holding_keeps_the_readers_choice(self, listening: Listening) -> None:
        listening.adopt(self._held_on(ChannelName.PULSE1, ChannelName.TRIANGLE), EVERY_CHANNEL)
        listening.set_channels(STEM_A, frozenset({ChannelName.PULSE1}))

        listening.adopt(self._held_on(ChannelName.PULSE1, ChannelName.TRIANGLE), EVERY_CHANNEL)

        assert listening.heard[STEM_A] == frozenset({ChannelName.PULSE1})

    def test_a_channel_a_recording_newly_reaches_joins_what_is_heard(self, listening: Listening) -> None:
        listening.adopt(self._held_on(ChannelName.PULSE1), EVERY_CHANNEL)
        listening.set_channels(STEM_A, frozenset({ChannelName.PULSE1}))

        listening.adopt(self._held_on(ChannelName.PULSE1, ChannelName.TRIANGLE), EVERY_CHANNEL)

        assert listening.heard[STEM_A] == frozenset({ChannelName.PULSE1, ChannelName.TRIANGLE})

    def test_a_channel_a_recording_stops_holding_leaves_what_is_heard(self, listening: Listening) -> None:
        listening.adopt(self._held_on(ChannelName.PULSE1, ChannelName.TRIANGLE), EVERY_CHANNEL)

        listening.adopt(self._held_on(ChannelName.PULSE1), EVERY_CHANNEL)

        assert listening.heard[STEM_A] == frozenset({ChannelName.PULSE1})

    def test_a_recording_leaving_the_record_leaves_the_choice(self, listening: Listening) -> None:
        """An edit letting a recording go takes its row away, and the rest keep what the reader chose."""
        listening.adopt(self._held_on(ChannelName.PULSE1, ChannelName.TRIANGLE), EVERY_CHANNEL)
        listening.set_channels(STEM_A, frozenset({ChannelName.PULSE1}))

        listening.adopt(
            _stems_data(ChannelAssignment(channel_name=ChannelName.PULSE1, stem_ids=[STEM_A, STEM_A])).without_entries(
                frozenset({STEM_B})
            ),
            EVERY_CHANNEL,
        )

        assert listening.offered == {STEM_A: frozenset({ChannelName.PULSE1})}
        assert listening.heard == {STEM_A: frozenset({ChannelName.PULSE1})}
        assert STEM_B not in listening.selection.stems_for(ChannelName.PULSE1)

    def test_a_released_choice_hears_the_next_document_whole(self, listening: Listening) -> None:
        listening.adopt(self._held_on(ChannelName.PULSE1, ChannelName.TRIANGLE), EVERY_CHANNEL)
        listening.set_channels(STEM_A, frozenset())

        listening.release()
        listening.adopt(self._held_on(ChannelName.PULSE1, ChannelName.TRIANGLE), EVERY_CHANNEL)

        assert listening.heard == listening.offered


class TestSoloingARecording:
    """A solo hears one recording alone and remembers the choice it replaced."""

    @staticmethod
    def _held() -> StemsData:
        return _stems_data(
            ChannelAssignment(channel_name=ChannelName.PULSE1, stem_ids=[STEM_A, STEM_B]),
            ChannelAssignment(channel_name=ChannelName.TRIANGLE, stem_ids=[STEM_A, STEM_B]),
        )

    def test_the_recording_is_heard_on_every_channel_it_offers_and_no_other_is_heard(
        self,
        listening: Listening,
    ) -> None:
        listening.adopt(self._held(), EVERY_CHANNEL)
        listening.set_channels(STEM_A, frozenset({ChannelName.PULSE1}))

        listening.solo(STEM_A)

        assert listening.heard[STEM_A] == frozenset({ChannelName.PULSE1, ChannelName.TRIANGLE})
        assert listening.heard[STEM_B] == frozenset()

    def test_a_second_solo_returns_to_the_choice_it_replaced(self, listening: Listening) -> None:
        listening.adopt(self._held(), EVERY_CHANNEL)
        listening.set_channels(STEM_B, frozenset({ChannelName.TRIANGLE}))
        before = listening.heard

        listening.solo(STEM_A)
        listening.solo(STEM_A)

        assert listening.heard == before

    def test_soloing_another_recording_keeps_the_choice_the_first_solo_replaced(
        self,
        listening: Listening,
    ) -> None:
        listening.adopt(self._held(), EVERY_CHANNEL)
        listening.set_channels(STEM_B, frozenset({ChannelName.TRIANGLE}))
        before = listening.heard

        listening.solo(STEM_A)
        listening.solo(STEM_B)
        listening.solo(STEM_B)

        assert listening.heard == before

    def test_a_solo_with_nothing_remembered_hears_every_recording_whole(self, listening: Listening) -> None:
        listening.adopt(self._held(), EVERY_CHANNEL)
        listening.solo(STEM_A)
        listening.adopt(self._held(), EVERY_CHANNEL)

        listening.solo(STEM_A)

        assert listening.heard == listening.offered

    def test_a_choice_made_by_hand_stands_as_the_new_state(self, listening: Listening) -> None:
        listening.adopt(self._held(), EVERY_CHANNEL)
        listening.solo(STEM_A)

        listening.set_channels(STEM_B, frozenset({ChannelName.PULSE1}))
        listening.solo(STEM_A)

        assert listening.heard[STEM_A] == frozenset({ChannelName.PULSE1, ChannelName.TRIANGLE})
        assert listening.heard[STEM_B] == frozenset()

    def test_a_recording_offering_nothing_leaves_the_others_heard(
        self,
        listening: Listening,
    ) -> None:
        listening.adopt(
            _stems_data(ChannelAssignment(channel_name=ChannelName.PULSE1, stem_ids=[STEM_A])), EVERY_CHANNEL
        )

        listening.solo(STEM_B)
        listening.solo(STEM_B)

        assert listening.heard == listening.offered


class TestTheChannelsKeptOn:
    """The boxes above the waveform are listening state: a fresh document plays every channel, a channel
    switched off stays off across an edit, and one coming into play joins the channels on.
    """

    def test_a_fresh_document_keeps_every_playing_channel_on(self, listening: Listening) -> None:
        listening.adopt(_stems_data(), PULSES)

        assert listening.playing == PULSES
        assert listening.channels_on == PULSES

    def test_a_channel_switched_off_stays_off_across_an_edit(self, listening: Listening) -> None:
        listening.adopt(_stems_data(), PULSES)
        listening.set_channels_on(frozenset({ChannelName.PULSE1}))

        listening.adopt(_stems_data(), PULSES)

        assert listening.channels_on == frozenset({ChannelName.PULSE1})

    def test_a_channel_coming_into_play_joins_the_channels_on(self, listening: Listening) -> None:
        listening.adopt(_stems_data(), frozenset({ChannelName.PULSE1}))
        listening.set_channels_on(frozenset())

        listening.adopt(_stems_data(), PULSES)

        assert listening.channels_on == frozenset({ChannelName.PULSE2})

    def test_a_channel_leaving_play_leaves_the_channels_on(self, listening: Listening) -> None:
        listening.adopt(_stems_data(), PULSES)

        listening.adopt(_stems_data(), frozenset({ChannelName.PULSE1}))

        assert listening.channels_on == frozenset({ChannelName.PULSE1})

    def test_a_choice_names_playing_channels_alone(self, listening: Listening) -> None:
        listening.adopt(_stems_data(), PULSES)

        listening.set_channels_on(EVERY_CHANNEL)

        assert listening.channels_on == PULSES

    def test_the_hearing_carries_both_choices(self, listening: Listening) -> None:
        listening.adopt(
            _stems_data(ChannelAssignment(channel_name=ChannelName.PULSE1, stem_ids=[STEM_A, STEM_B])), PULSES
        )
        listening.set_channels(STEM_B, frozenset())
        listening.set_channels_on(frozenset({ChannelName.PULSE1}))

        hearing = listening.hearing

        assert hearing.selection.stems_for(ChannelName.PULSE1) == frozenset({STEM_A})
        assert hearing.channels_on == frozenset({ChannelName.PULSE1})

    def test_a_released_choice_leaves_nothing_on(self, listening: Listening) -> None:
        listening.adopt(_stems_data(), PULSES)

        listening.release()

        assert listening.playing == frozenset()
        assert listening.channels_on == frozenset()
