from typing import Final

from sampletones_application.logic.history.action import HistoryAction
from tests.suite.history.gestures import GESTURES_BY_LABEL, LEAD_REGION, perform
from tests.suite.history.projects import LEAD
from tests.suite.history.session import HistorySession

BLANK_NAME: Final[str] = "   "


class TestAGestureChangingNothingRecordsNothing:
    """A gesture that leaves the project as it stands adds no entry; the same path acting afterwards adds one."""

    def test_the_properties_confirmed_unchanged(self, session: HistorySession) -> None:
        info = session.project.info
        settings = session.project.settings

        session.audit.refused(
            lambda: session.app.project_properties_window.on_commit(
                info.title,
                info.author,
                info.comment,
                settings.first_highlight,
                settings.second_highlight,
            )
        )

        perform(session, GESTURES_BY_LABEL["edit the properties"])
        assert len(session.history.entries) == 2

    def test_the_rate_the_project_runs_at(self, session: HistorySession) -> None:
        session.sequencer._nes_frequency_change_acknowledged = True

        session.audit.refused(
            lambda: session.sequencer._sequencer_module_panel.on_nes_frequency(
                session.project.settings.nes_frequency,
            )
        )

        perform(session, GESTURES_BY_LABEL["retune the project"])
        assert len(session.history.entries) == 2

    def test_a_blank_name(self, session: HistorySession) -> None:
        voices = session.sequencer._sequencer_voices_panel

        session.audit.refused(lambda: voices.on_rename_committed(session.voice_id(LEAD), BLANK_NAME))

        perform(session, GESTURES_BY_LABEL["rename a sample"])
        assert len(session.history.entries) == 2

    def test_a_copy_reading_the_tracker(self, session: HistorySession) -> None:
        tracker = session.sequencer._sequencer_tracker_panel
        cut = GESTURES_BY_LABEL["cut a tracker block"]

        session.audit.refused(lambda: tracker.on_copy_block(LEAD_REGION))

        perform(session, cut)
        assert [entry.action for entry in session.history.entries][1:] == [HistoryAction.CUT_BLOCK]


class TestAStepPastEitherEnd:
    """Undo at the first entry and redo at the last change nothing; inside the stack they move."""

    def test_an_undo_at_the_start(self, session: HistorySession) -> None:
        session.audit.undo()
        perform(session, GESTURES_BY_LABEL["set the tempo"])

        session.audit.undo()

        assert session.history.cursor == 0

    def test_a_redo_at_the_end(self, session: HistorySession) -> None:
        perform(session, GESTURES_BY_LABEL["set the tempo"])
        session.audit.redo()

        session.audit.undo()
        session.audit.redo()

        assert session.history.cursor == 1

    def test_a_jump_past_the_end_and_onto_the_cursor(self, session: HistorySession) -> None:
        perform(session, GESTURES_BY_LABEL["set the tempo"])
        session.audit.jump_to(len(session.history.entries))
        session.audit.jump_to(session.history.cursor)

        session.audit.jump_to(0)

        assert session.history.cursor == 0
