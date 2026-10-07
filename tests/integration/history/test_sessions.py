from pathlib import Path
from typing import Final, Iterator, List
from unittest.mock import PropertyMock, patch

import pytest

from sampletones_application.config.managers.session import SessionManager
from sampletones_application.logic.history.action import HistoryAction
from sampletones_core.constants.enums import ChannelName, FeatureKey
from sampletones_core.features.envelope import Envelope
from sampletones_core.project.voices.note_on import NoteOn
from sampletones_core.project.voices.sample import Sample
from tests.suite.history.gestures import EDITED_ENVELOPE, GESTURES_BY_LABEL, perform
from tests.suite.history.projects import BASS, LEAD, PAD
from tests.suite.history.session import HistorySession, history_session

TIGHT_BUDGET: Final[int] = 5
LEAD_ENVELOPE: Final[Envelope[int]] = Envelope[int](items=(13, 10))
COPY_ENVELOPE: Final[Envelope[int]] = Envelope[int](items=(3, 2))
ORIGINAL_ENVELOPE: Final[Envelope[int]] = Envelope[int](items=(8, 4))
COLLISION: Final[str] = "Two samples carrying one reconstruction id are stored as one reconstruction"


@pytest.fixture
def tight_session(tmp_path: Path) -> Iterator[HistorySession]:
    """The every-part project under a history keeping the last few entries alone."""
    with (
        patch.object(SessionManager, "history_budget", new_callable=PropertyMock, return_value=TIGHT_BUDGET),
        history_session(tmp_path) as opened,
    ):
        yield opened


def _gesture(
    session: HistorySession,
    label: str,
) -> None:
    perform(session, GESTURES_BY_LABEL[label])


def _edit(
    session: HistorySession,
    sample: Sample,
    channel_name: ChannelName,
    envelope: Envelope[int],
) -> None:
    session.open_voice_id(sample.id)
    session.audit.perform(
        lambda: session.instruments.handle_envelope_changed(channel_name, FeatureKey.VOLUME, envelope),
        action=HistoryAction.EDIT_RECONSTRUCTION,
        target=(sample.id,),
    )


def _rows_naming(
    session: HistorySession,
    voice_id: str,
) -> int:
    return sum(
        1
        for channel in session.project.song.channels.values()
        for pattern in channel.patterns.values()
        for row in pattern.rows
        if isinstance(row.command, NoteOn) and row.command.voice_id == voice_id
    )


def _last_sample(session: HistorySession) -> Sample:
    voice = list(session.project.voices)[-1]
    assert isinstance(voice, Sample)
    return voice


def _end_with_a_reload(session: HistorySession) -> None:
    session.save()
    assert session.stored_fingerprint() == session.audit.model.live.fingerprint


class TestAReconstructionsTabSession:
    """Edits of one sample's channels, a removal and a rate between sequencer typing, undone and redone."""

    def test_every_state_comes_back(self, session: HistorySession) -> None:
        lead = session.sample(LEAD)
        _edit(session, lead, ChannelName.PULSE1, LEAD_ENVELOPE)
        _edit(session, lead, ChannelName.PULSE2, LEAD_ENVELOPE)
        _gesture(session, "type a volume")
        _gesture(session, "remove a recording")
        _gesture(session, "retune the project with a sample open")
        _gesture(session, "edit an instrument's envelope")
        assert [entry.action for entry in session.history.entries] == [
            HistoryAction.INITIAL,
            HistoryAction.EDIT_RECONSTRUCTION,
            HistoryAction.EDIT_ROW,
            HistoryAction.EDIT_RECONSTRUCTION,
            HistoryAction.SET_NES_FREQUENCY,
            HistoryAction.EDIT_INSTRUMENT,
        ]

        for _ in range(3):
            session.audit.undo()
        session.audit.redo()
        _gesture(session, "type a step")

        assert len(session.history.entries) == 5
        session.audit.walk()
        _end_with_a_reload(session)


class TestADuplicateEditedApart:
    """A copy edited apart from its original keeps the two documents apart through every step."""

    def _diverge(self, session: HistorySession) -> None:
        _gesture(session, "duplicate a sample")
        _edit(session, _last_sample(session), ChannelName.NOISE, COPY_ENVELOPE)
        session.audit.undo()
        _edit(session, session.sample(BASS), ChannelName.NOISE, ORIGINAL_ENVELOPE)

    def test_every_state_comes_back(self, session: HistorySession) -> None:
        self._diverge(session)

        session.audit.walk()

        assert session.sample(BASS).reconstruction is not _last_sample(session).reconstruction

    @pytest.mark.xfail(strict=True, reason=COLLISION)
    def test_a_save_keeps_both_documents(self, session: HistorySession) -> None:
        self._diverge(session)

        _end_with_a_reload(session)


class TestTheSavePointThroughASession:
    """The saved entry reads clean wherever the cursor meets it, until a commit truncates it away."""

    def test_clean_and_dirty_follow_the_saved_entry(self, session: HistorySession) -> None:
        _gesture(session, "set the tempo")
        session.save()
        _gesture(session, "set the tempo")
        session.audit.undo()
        assert not session.controller.is_dirty
        session.audit.undo()
        assert session.controller.is_dirty
        session.audit.redo()
        _gesture(session, "set the speed")
        session.audit.undo()
        assert not session.controller.is_dirty

        session.audit.jump_to(0)
        _gesture(session, "edit the properties")
        session.audit.walk()

        assert session.audit.model.saved is None
        assert session.controller.is_dirty
        _end_with_a_reload(session)


class TestATightBudget:
    """The budget keeps the newest entries, each still restoring its state, and drops the opened state."""

    def test_the_kept_entries_restore_their_states(self, tight_session: HistorySession) -> None:
        session = tight_session
        for label in (
            "set the tempo",
            "type a note with an instrument",
            "insert a frame",
            "rename a sample",
            "set the speed",
            "add an instrument",
            "edit the properties",
        ):
            _gesture(session, label)

        assert len(session.history.entries) == TIGHT_BUDGET
        assert session.history.entries[0].action is not HistoryAction.INITIAL
        session.audit.walk()
        session.audit.jump_to(0)
        _gesture(session, "set the tempo")
        assert len(session.history.entries) == 2


class TestAVoiceTheSongNames:
    """Removing a voice clears the rows naming it, and an undo brings both the voice and its rows back."""

    def test_the_rows_return_with_the_voice(self, session: HistorySession) -> None:
        lead = session.voice_id(LEAD)
        named: List[int] = [_rows_naming(session, lead)]

        _gesture(session, "remove a sample")
        named.append(_rows_naming(session, lead))
        session.audit.undo()
        named.append(_rows_naming(session, lead))
        session.audit.redo()
        named.append(_rows_naming(session, lead))

        assert named[0] > 0
        assert named == [named[0], 0, named[0], 0]
        _end_with_a_reload(session)


class TestTheProjectLifecycle:
    """A new, an opened and a closed project each start the stack over from what they put in place."""

    def test_each_transition_starts_over(self, session: HistorySession) -> None:
        _gesture(session, "set the tempo")

        session.audit.transition(session.app._project_coordinator.new_project)
        assert len(session.history.entries) == 1
        session.audit.perform(
            lambda: session.sequencer._sequencer_module_panel.on_speed(4),
            action=HistoryAction.SET_SPEED,
            target=(),
        )

        session.audit.transition(session.app._project_coordinator.close_project)
        assert len(session.history.entries) == 0

        session.reopen()
        assert len(session.history.entries) == 1
        _gesture(session, "edit an instrument's envelope")
        session.audit.walk()
        assert session.instrument(PAD).envelopes.volume == EDITED_ENVELOPE
