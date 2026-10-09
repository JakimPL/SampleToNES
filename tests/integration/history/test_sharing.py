from typing import Dict

from sampletones_core.constants.enums import ChannelName
from sampletones_core.project import Project
from sampletones_core.project.voices.instrument import Instrument
from sampletones_core.project.voices.sample import Sample
from sampletones_core.reconstructions import Reconstruction
from tests.suite.history.gestures import GESTURES_BY_LABEL, perform
from tests.suite.history.projects import FIRST_PATTERN, LEAD, PAD
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

    def test_a_tracker_edit_shares_every_other_pattern(self, session: HistorySession) -> None:
        perform(session, GESTURES_BY_LABEL["type a note with a sample"])

        before, after = _entry(session, 0).song.channels, _entry(session, 1).song.channels
        for name, channel in after.items():
            for index, pattern in channel.patterns.items():
                edited = name is ChannelName.PULSE1 and index == FIRST_PATTERN
                assert (pattern is before[name].patterns[index]) is not edited

    def test_an_instrument_edit_shares_every_other_voice(self, session: HistorySession) -> None:
        pad = session.voice_id(PAD)

        perform(session, GESTURES_BY_LABEL["edit an instrument's envelope"])

        before = {voice.id: voice for voice in _entry(session, 0).voices}
        after = {voice.id: voice for voice in _entry(session, 1).voices}
        for voice_id, voice in after.items():
            match voice:
                case Instrument():
                    held = before[voice_id]
                    assert isinstance(held, Instrument)
                    assert (voice.envelopes is held.envelopes) is (voice_id != pad)
                case Sample():
                    held = before[voice_id]
                    assert isinstance(held, Sample)
                    assert voice.reconstruction is held.reconstruction
