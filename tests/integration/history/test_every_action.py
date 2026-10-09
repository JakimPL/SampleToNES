import pytest

from tests.suite.history.gestures import GESTURES, Gesture, perform
from tests.suite.history.projects import LEAD
from tests.suite.history.session import HistorySession


def _label(gesture: Gesture) -> str:
    return gesture.label


class TestEveryGestureAlone:
    """Each gesture records one entry, and every way through the history reproduces each state."""

    @pytest.mark.parametrize("gesture", GESTURES, ids=_label)
    def test_one_entry_its_undo_and_redo_restore(
        self,
        session: HistorySession,
        gesture: Gesture,
    ) -> None:
        perform(session, gesture)

        assert [entry.action for entry in session.history.entries][1:] == [gesture.action]
        session.audit.walk()

    @pytest.mark.parametrize("gesture", GESTURES, ids=_label)
    def test_a_save_stores_the_state_and_an_undo_returns_to_the_file(
        self,
        session: HistorySession,
        gesture: Gesture,
    ) -> None:
        opened = session.stored_fingerprint()
        perform(session, gesture)

        session.save()
        assert session.stored_fingerprint() == session.audit.model.live.fingerprint

        session.audit.undo()
        session.save()
        assert session.stored_fingerprint() == opened

    @pytest.mark.parametrize("gesture", GESTURES, ids=_label)
    def test_the_open_sample_follows_every_step(
        self,
        session: HistorySession,
        gesture: Gesture,
    ) -> None:
        session.open_voice(LEAD)

        perform(session, gesture)

        session.audit.walk()
