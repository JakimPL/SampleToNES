from typing import Dict

from sampletones_core.constants.enums import ChannelName
from sampletones_core.project import Project
from sampletones_core.project.voices.sample import Sample
from sampletones_core.reconstructions import Reconstruction
from tests.suite.history.gestures import GESTURES_BY_LABEL, perform
from tests.suite.history.projects import LEAD
from tests.suite.history.session import HistorySession


def _documents(project: Project) -> Dict[str, Reconstruction]:
    return {voice.id: voice.reconstruction for voice in project.voices if isinstance(voice, Sample)}


def _entry(
    session: HistorySession,
    index: int,
) -> Project:
    return session.history.entries[index].project


class TestAnEntryOwnsWhatItsGestureReplaced:
    """Consecutive entries share every part of the project the gesture between them left alone."""

    def test_a_tracker_edit_shares_every_document(self, session: HistorySession) -> None:
        perform(session, GESTURES_BY_LABEL["type a note with a sample"])

        before, after = _documents(_entry(session, 0)), _documents(_entry(session, 1))

        assert all(after[voice_id] is document for voice_id, document in before.items())

    def test_a_channel_edit_shares_the_other_samples_and_channels(self, session: HistorySession) -> None:
        lead = session.voice_id(LEAD)

        perform(session, GESTURES_BY_LABEL["edit a channel's envelope"])

        before, after = _documents(_entry(session, 0)), _documents(_entry(session, 1))
        assert all(after[voice_id] is document for voice_id, document in before.items() if voice_id != lead)
        assert after[lead] is not before[lead]
        assert after[lead].streams[ChannelName.PULSE2] is before[lead].streams[ChannelName.PULSE2]

    def test_a_retune_shares_every_stream(self, session: HistorySession) -> None:
        perform(session, GESTURES_BY_LABEL["retune the project"])

        before, after = _documents(_entry(session, 0)), _documents(_entry(session, 1))
        for voice_id, document in before.items():
            assert after[voice_id] is not document
            assert all(
                left is right
                for left, right in zip(after[voice_id].instructions_data, document.instructions_data, strict=True)
            )
