from dataclasses import dataclass
from typing import Final, FrozenSet, List

import pytest

from sampletones_application.logic.reconstruction.listening import Listening
from sampletones_core.constants.algorithm import AUTHORED_STEM_ID, RESTING_STEM_ID
from sampletones_core.constants.enums import ChannelName, bending_channels
from sampletones_core.instructions import PulseInstruction
from sampletones_core.reconstructions import Reconstruction
from sampletones_core.reconstructions.reconstruction.stems.channel_assignment import ChannelAssignment
from sampletones_core.reconstructions.reconstruction.stems.data import StemsData
from sampletones_core.reconstructions.reconstruction.stems.hearing import (
    carried_hearing,
    offered_channels,
    whole_hearing,
)
from sampletones_core.reconstructions.reconstructor.stems.configs.config import StemsConfig
from sampletones_core.reconstructions.reconstructor.stems.configs.entry import StemEntry
from sampletones_core.reconstructions.reconstructor.stems.configs.hierarchy import StemsHierarchy
from sampletones_core.reconstructions.reconstructor.stems.configs.settings import StemSettings
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase
from tests.suite.stems import RECORDED_SCALE, SHARED_CHANNEL, TAKING_TURNS_PITCH, taking_turns

__all__ = ["taking_turns"]

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


class TestTheChoiceIsCarriedByTheCoreRule(BaseTestSuite):
    """Adopting a record carries the choice by the rule the regeneration worker carries it by, so the hearing
    the listening makes on a landed document is the one the worker rendered and exported for.
    """

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        before: StemsData
        playing_before: FrozenSet[ChannelName]
        chosen: FrozenSet[ChannelName]
        after: StemsData
        playing_after: FrozenSet[ChannelName]

    test_cases = (
        TestCase(
            label="a record kept as it was",
            before=_stems_data(ChannelAssignment(channel_name=ChannelName.PULSE1, stem_ids=[STEM_A, STEM_B])),
            playing_before=PULSES,
            chosen=frozenset({ChannelName.PULSE1}),
            after=_stems_data(ChannelAssignment(channel_name=ChannelName.PULSE1, stem_ids=[STEM_A, STEM_B])),
            playing_after=PULSES,
        ),
        TestCase(
            label="a recording newly reaching a channel",
            before=_stems_data(ChannelAssignment(channel_name=ChannelName.PULSE1, stem_ids=[STEM_A, STEM_B])),
            playing_before=PULSES,
            chosen=frozenset(),
            after=_stems_data(
                ChannelAssignment(channel_name=ChannelName.PULSE1, stem_ids=[STEM_A, STEM_B]),
                ChannelAssignment(channel_name=ChannelName.TRIANGLE, stem_ids=[STEM_A]),
            ),
            playing_after=EVERY_CHANNEL,
        ),
        TestCase(
            label="the reader's own row appearing while a recording is muted",
            before=_stems_data(ChannelAssignment(channel_name=ChannelName.PULSE1, stem_ids=[STEM_A, STEM_B])),
            playing_before=PULSES,
            chosen=frozenset(),
            after=_stems_data(
                ChannelAssignment(channel_name=ChannelName.PULSE1, stem_ids=[STEM_A, STEM_B, AUTHORED_STEM_ID])
            ),
            playing_after=frozenset({ChannelName.PULSE1}),
        ),
        TestCase(
            label="a recording leaving the record",
            before=_stems_data(
                ChannelAssignment(channel_name=ChannelName.PULSE1, stem_ids=[STEM_A, STEM_B]),
                ChannelAssignment(channel_name=ChannelName.TRIANGLE, stem_ids=[STEM_B]),
            ),
            playing_before=EVERY_CHANNEL,
            chosen=frozenset({ChannelName.PULSE1}),
            after=_stems_data(
                ChannelAssignment(channel_name=ChannelName.PULSE1, stem_ids=[STEM_A, STEM_A])
            ).without_entries(frozenset({STEM_B})),
            playing_after=PULSES,
        ),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda case: case.label)
    def test_adopting_a_record_hears_what_the_rule_carries(self, listening: Listening, test_case: TestCase) -> None:
        listening.adopt(test_case.before, test_case.playing_before)
        listening.set_channels(STEM_A, test_case.chosen)
        listening.set_channels_on(frozenset({ChannelName.PULSE1}))
        expected = carried_hearing(
            listening.hearing,
            offered_before=listening.offered,
            playing_before=listening.playing,
            offered_after=offered_channels(test_case.after),
            playing_after=test_case.playing_after,
        )

        listening.adopt(test_case.after, test_case.playing_after)

        assert listening.hearing == expected

    def test_a_fresh_document_is_heard_as_the_whole_hearing(
        self,
        listening: Listening,
        taking_turns: Reconstruction,
    ) -> None:
        """A preview of a document keys the cache the way the tab keys the same document opened afresh."""
        shared = taking_turns.instructions[SHARED_CHANNEL]
        edited = taking_turns.with_channel_data(
            SHARED_CHANNEL,
            [PulseInstruction(on=True, pitch=TAKING_TURNS_PITCH, volume=8, duty_cycle=0)] * (len(shared) + 1),
            TAKING_TURNS_PITCH,
            (),
            heard=taking_turns.recorded_stem_ids,
        )

        listening.adopt(edited.stems_data, frozenset(edited.playing_channels))

        assert listening.hearing == whole_hearing(edited)


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

    def test_a_record_adopted_forgets_the_choice_a_solo_replaced(self, listening: Listening) -> None:
        """An edit landing between two solos ends the first solo's memory, so the second hears the whole record."""
        listening.adopt(self._held(), EVERY_CHANNEL)
        listening.set_channels(STEM_B, frozenset({ChannelName.TRIANGLE}))
        listening.solo(STEM_A)

        listening.adopt(self._held(), EVERY_CHANNEL)
        listening.solo(STEM_A)

        assert listening.heard == listening.offered

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
