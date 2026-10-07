from contextlib import contextmanager
from typing import Final, Iterator, List
from unittest.mock import patch

import pytest

from sampletones_application.logic.history.action import HistoryAction
from sampletones_application.logic.reconstruction.rewrites.steps import StemRemovalRequest
from sampletones_application.utils.callbacks.queue import CallbackQueue
from sampletones_application.utils.parallelization.thread import SingleThreadExecutor
from sampletones_core.constants.enums import ChannelName, FeatureKey
from sampletones_core.features.envelope import Envelope
from sampletones_core.project.voices.sample import Sample
from tests.suite.application import HeldQueue
from tests.suite.history.audit import immediately
from tests.suite.history.gestures import GESTURES_BY_LABEL, REMOVED_STEM_NAME, RETUNED_RATE, perform
from tests.suite.history.projects import BASS, LEAD
from tests.suite.history.session import HistorySession
from tests.suite.stems import STEM_B_ID

FIRST_ENVELOPE: Final[Envelope[int]] = Envelope[int](items=(11, 9))
REFUSED_ENVELOPE: Final[Envelope[int]] = Envelope[int](items=(1, 1))
SECOND_ENVELOPE: Final[Envelope[int]] = Envelope[int](items=(6, 5))
LATE_RETUNE: Final[str] = (
    "Retune results landing after another commit record an entry of their own, so one undo leaves the new rate "
    "over samples at the old one"
)


@contextmanager
def held_reports(session: HistorySession) -> Iterator[HeldQueue]:
    """Holds what the workers report until the case drains it, each gesture meanwhile landing what it does at once."""
    queue = HeldQueue()
    with patch.object(CallbackQueue, "add", queue.add), session.audit.settling(immediately):
        yield queue


def _edit_lead(
    session: HistorySession,
    channel_name: ChannelName,
    envelope: Envelope[int],
) -> None:
    session.instruments.handle_envelope_changed(channel_name, FeatureKey.VOLUME, envelope)


def _actions(session: HistorySession) -> List[HistoryAction]:
    return [entry.action for entry in session.history.entries]


def _lead_volumes(
    session: HistorySession,
    channel_name: ChannelName,
) -> List[int]:
    return [instruction.volume for instruction in session.sample(LEAD).reconstruction.instructions[channel_name]]


class TestARebuildStillOnItsWay:
    """A channel rebuild lands after the gestures made while it ran, and a whole-document gesture waits for it."""

    def test_a_tracker_edit_lands_first(self, session: HistorySession) -> None:
        session.open_voice(LEAD)
        lead = session.voice_id(LEAD)

        with held_reports(session) as queue:
            _edit_lead(session, ChannelName.PULSE1, FIRST_ENVELOPE)
            SingleThreadExecutor.join_all()
            session.audit.check()
            perform(session, GESTURES_BY_LABEL["type a volume"])
            queue.drain()

        session.audit.adopt_landed([(HistoryAction.EDIT_RECONSTRUCTION, (lead,))])
        session.audit.check()
        assert _actions(session) == [HistoryAction.INITIAL, HistoryAction.EDIT_ROW, HistoryAction.EDIT_RECONSTRUCTION]
        session.audit.walk()

    def test_an_undo_waits_and_undoes_the_edit(self, session: HistorySession) -> None:
        perform(session, GESTURES_BY_LABEL["set the tempo"])
        session.open_voice(LEAD)
        lead = session.voice_id(LEAD)

        with held_reports(session) as queue:
            _edit_lead(session, ChannelName.PULSE1, FIRST_ENVELOPE)
            SingleThreadExecutor.join_all()
            session.sequencer.undo()
            session.audit.check()
            queue.drain()

        session.audit.adopt_landed([(HistoryAction.EDIT_RECONSTRUCTION, (lead,))])
        session.audit.model.undo()
        session.audit.check()
        assert session.history.cursor == 1
        session.audit.walk()

    def test_a_save_waits_and_writes_the_edit(self, session: HistorySession) -> None:
        session.open_voice(LEAD)
        lead = session.voice_id(LEAD)
        opened = session.stored_fingerprint()

        with held_reports(session) as queue:
            _edit_lead(session, ChannelName.PULSE1, FIRST_ENVELOPE)
            SingleThreadExecutor.join_all()
            session.save_door()
            assert session.stored_fingerprint() == opened
            queue.drain()

        session.audit.adopt_landed([(HistoryAction.EDIT_RECONSTRUCTION, (lead,))])
        session.audit.model.save()
        session.audit.check()
        assert session.stored_fingerprint() == session.audit.model.live.fingerprint

    def test_a_change_drawn_while_a_removal_waits_goes_nowhere(self, session: HistorySession) -> None:
        session.open_voice(LEAD)
        lead = session.voice_id(LEAD)

        with held_reports(session) as queue:
            _edit_lead(session, ChannelName.PULSE1, FIRST_ENVELOPE)
            session.app._reconstruction_coordinator.request_rewrite(
                StemRemovalRequest(stem_id=STEM_B_ID, stem_name=REMOVED_STEM_NAME)
            )
            _edit_lead(session, ChannelName.PULSE1, REFUSED_ENVELOPE)
            SingleThreadExecutor.join_all()
            queue.drain()

        session.audit.adopt_landed(
            [
                (HistoryAction.EDIT_RECONSTRUCTION, (lead,)),
                (HistoryAction.EDIT_RECONSTRUCTION, None),
            ]
        )
        session.audit.check()
        assert REFUSED_ENVELOPE.items[0] not in _lead_volumes(session, ChannelName.PULSE1)
        session.audit.walk()

        session.audit.perform(
            lambda: _edit_lead(session, ChannelName.PULSE1, SECOND_ENVELOPE),
            action=HistoryAction.EDIT_RECONSTRUCTION,
            target=(lead,),
        )
        assert SECOND_ENVELOPE.items[0] in _lead_volumes(session, ChannelName.PULSE1)


class TestEditsOfOneSampleRunTogether:
    """Consecutive edits of one sample make one entry whatever channels they move, until another gesture comes."""

    def test_two_channels_make_one_entry(self, session: HistorySession) -> None:
        session.open_voice(LEAD)
        lead = session.voice_id(LEAD)

        for channel_name in (ChannelName.PULSE1, ChannelName.PULSE2):
            session.audit.perform(
                lambda: _edit_lead(session, channel_name, SECOND_ENVELOPE),
                action=HistoryAction.EDIT_RECONSTRUCTION,
                target=(lead,),
            )

        assert _actions(session) == [HistoryAction.INITIAL, HistoryAction.EDIT_RECONSTRUCTION]
        session.audit.walk()

    def test_an_edit_of_another_sample_between_keeps_them_apart(self, session: HistorySession) -> None:
        lead = session.voice_id(LEAD)
        bass = session.voice_id(BASS)
        steps = ((LEAD, lead, ChannelName.PULSE1), (BASS, bass, ChannelName.NOISE), (LEAD, lead, ChannelName.PULSE2))

        for name, voice_id, channel_name in steps:
            session.open_voice(name)
            session.audit.perform(
                lambda: session.instruments.handle_envelope_changed(channel_name, FeatureKey.VOLUME, SECOND_ENVELOPE),
                action=HistoryAction.EDIT_RECONSTRUCTION,
                target=(voice_id,),
            )

        assert len(session.history.entries) == 4
        session.audit.walk()


class TestARateChangeAndTheRetuneAfterIt:
    """A rate change records one entry that the retuned samples join, so one undo restores the rate and the audio."""

    def test_the_retune_joins_the_rate_change(self, session: HistorySession) -> None:
        perform(session, GESTURES_BY_LABEL["retune the project"])

        session.audit.undo()

        assert session.history.cursor == 0
        assert all(
            sample.reconstruction.config.nes_frequency == session.project.settings.nes_frequency
            for sample in session.project.voices
            if isinstance(sample, Sample)
        )

    @pytest.mark.xfail(strict=True, reason=LATE_RETUNE)
    def test_a_tracker_edit_before_the_retune_lands(self, session: HistorySession) -> None:
        session.sequencer._nes_frequency_change_acknowledged = True

        with held_reports(session) as queue:
            session.audit.perform(
                lambda: session.sequencer._sequencer_module_panel.on_nes_frequency(RETUNED_RATE),
                action=HistoryAction.SET_NES_FREQUENCY,
                target=(RETUNED_RATE,),
            )
            perform(session, GESTURES_BY_LABEL["type a volume"])
            SingleThreadExecutor.join_all()
            queue.drain()

        assert _actions(session) == [
            HistoryAction.INITIAL,
            HistoryAction.SET_NES_FREQUENCY,
            HistoryAction.EDIT_ROW,
        ]
