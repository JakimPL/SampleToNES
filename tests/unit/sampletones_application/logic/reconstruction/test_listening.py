from typing import Final, List

import pytest

from sampletones_application.logic.reconstruction.listening import StemListening, offered_channels
from sampletones_core.constants.algorithm import AUTHORED_STEM_ID, RESTING_STEM_ID
from sampletones_core.constants.enums import ChannelName, bending_channels
from sampletones_core.reconstructions.reconstruction.stems.channel_assignment import ChannelAssignment
from sampletones_core.reconstructions.reconstruction.stems.data import StemsData
from sampletones_core.reconstructions.reconstructor.stems.configs.config import StemsConfig
from sampletones_core.reconstructions.reconstructor.stems.configs.entry import StemEntry
from sampletones_core.reconstructions.reconstructor.stems.configs.hierarchy import StemsHierarchy
from sampletones_core.reconstructions.reconstructor.stems.configs.settings import StemSettings

STEM_A: Final[int] = 0
STEM_B: Final[int] = 1
STEM_CHANNELS: Final[List[ChannelName]] = [ChannelName.PULSE1, ChannelName.TRIANGLE]


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
    )


@pytest.fixture
def listening() -> StemListening:
    return StemListening()


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
    def test_every_recording_is_heard_everywhere_it_holds_frames(self, listening: StemListening) -> None:
        stems_data = _stems_data(
            ChannelAssignment(channel_name=ChannelName.PULSE1, stem_ids=[STEM_A, STEM_B]),
            ChannelAssignment(channel_name=ChannelName.TRIANGLE, stem_ids=[STEM_A, RESTING_STEM_ID]),
        )

        listening.adopt(stems_data)

        assert listening.heard == listening.offered

    def test_the_selection_answers_each_channel_with_the_recordings_on_it(self, listening: StemListening) -> None:
        stems_data = _stems_data(
            ChannelAssignment(channel_name=ChannelName.PULSE1, stem_ids=[STEM_A, STEM_B]),
            ChannelAssignment(channel_name=ChannelName.TRIANGLE, stem_ids=[STEM_A, RESTING_STEM_ID]),
        )

        listening.adopt(stems_data)

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

    def test_a_channel_a_recording_keeps_holding_keeps_the_readers_choice(self, listening: StemListening) -> None:
        listening.adopt(self._held_on(ChannelName.PULSE1, ChannelName.TRIANGLE))
        listening.set_channels(STEM_A, frozenset({ChannelName.PULSE1}))

        listening.adopt(self._held_on(ChannelName.PULSE1, ChannelName.TRIANGLE))

        assert listening.heard[STEM_A] == frozenset({ChannelName.PULSE1})

    def test_a_channel_a_recording_newly_reaches_joins_what_is_heard(self, listening: StemListening) -> None:
        listening.adopt(self._held_on(ChannelName.PULSE1))
        listening.set_channels(STEM_A, frozenset({ChannelName.PULSE1}))

        listening.adopt(self._held_on(ChannelName.PULSE1, ChannelName.TRIANGLE))

        assert listening.heard[STEM_A] == frozenset({ChannelName.PULSE1, ChannelName.TRIANGLE})

    def test_a_channel_a_recording_stops_holding_leaves_what_is_heard(self, listening: StemListening) -> None:
        listening.adopt(self._held_on(ChannelName.PULSE1, ChannelName.TRIANGLE))

        listening.adopt(self._held_on(ChannelName.PULSE1))

        assert listening.heard[STEM_A] == frozenset({ChannelName.PULSE1})

    def test_a_released_choice_hears_the_next_document_whole(self, listening: StemListening) -> None:
        listening.adopt(self._held_on(ChannelName.PULSE1, ChannelName.TRIANGLE))
        listening.set_channels(STEM_A, frozenset())

        listening.release()
        listening.adopt(self._held_on(ChannelName.PULSE1, ChannelName.TRIANGLE))

        assert listening.heard == listening.offered
