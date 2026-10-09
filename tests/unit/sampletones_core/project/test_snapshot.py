from typing import Final

import pytest

from sampletones_core.constants.enums import ChannelName, FeatureKey
from sampletones_core.features.envelope import Envelope
from sampletones_core.project import Project
from sampletones_core.project.patterns.pitch import Note
from sampletones_core.project.patterns.row import Row
from sampletones_core.project.voices.instrument import Instrument
from sampletones_core.project.voices.note_on import NoteOn
from sampletones_core.project.voices.sample import Sample
from tests.suite.history.audit import fresh_fingerprint
from tests.suite.history.projects import FIRST_PATTERN, LEAD, PAD, SECOND_PATTERN, every_part_project

EDITED_ROW: Final[int] = 1
EDITED_TEMPO: Final[int] = 99
SHORTER: Final[int] = 4
EDITED_VOLUME: Final[Envelope[int]] = Envelope[int](items=(3,))


@pytest.fixture
def project() -> Project:
    return every_part_project()


def _sample(
    project: Project,
    name: str,
) -> Sample:
    return next(voice for voice in project.voices if isinstance(voice, Sample) and voice.name == name)


def _instrument(
    project: Project,
    name: str,
) -> Instrument:
    return next(voice for voice in project.voices if isinstance(voice, Instrument) and voice.name == name)


class TestASnapshotKeepsItsOwnShells:
    """A snapshot reads as the project it was taken from, and an edit of either leaves the other as it was."""

    def test_it_reads_as_the_project(self, project: Project) -> None:
        assert fresh_fingerprint(project.snapshot()) == fresh_fingerprint(project)

    def test_a_row_written_after_it_leaves_it_as_it_was(self, project: Project) -> None:
        snapshot = project.snapshot()
        before = fresh_fingerprint(snapshot)
        lead = _sample(project, LEAD)

        project.song.channels[ChannelName.PULSE1].set_row(
            FIRST_PATTERN,
            EDITED_ROW,
            Row(command=NoteOn(voice_id=lead.id), pitch=Note(value=50)),
        )

        assert fresh_fingerprint(snapshot) == before
        assert fresh_fingerprint(project) != before

    def test_an_order_written_after_it_leaves_it_as_it_was(self, project: Project) -> None:
        snapshot = project.snapshot()

        project.song.set_order_entry(0, ChannelName.PULSE1, SECOND_PATTERN)

        assert snapshot.song.order[0][ChannelName.PULSE1] == FIRST_PATTERN

    def test_a_setting_a_name_and_a_move_leave_it_as_it_was(self, project: Project) -> None:
        snapshot = project.snapshot()
        before = fresh_fingerprint(snapshot)
        lead = _sample(project, LEAD)

        project.settings.tempo = EDITED_TEMPO
        lead.name = f"{LEAD} again"
        project.voices.move(lead.id, len(project.voices) - 1)

        assert fresh_fingerprint(snapshot) == before
        assert _sample(snapshot, LEAD).name == LEAD

    def test_an_envelope_written_after_it_leaves_it_as_it_was(self, project: Project) -> None:
        snapshot = project.snapshot()
        pad = _instrument(project, PAD)
        held = _instrument(snapshot, PAD).envelopes

        pad.envelopes = pad.envelopes.with_envelope(FeatureKey.VOLUME, EDITED_VOLUME)
        pad.invalidate()

        assert _instrument(snapshot, PAD).envelopes is held


class TestASnapshotHoldsTheVeryValues:
    """A snapshot copies the shells around the values and holds the values themselves."""

    def test_documents_envelopes_and_patterns_are_shared(self, project: Project) -> None:
        snapshot = project.snapshot()

        assert _sample(snapshot, LEAD).reconstruction is _sample(project, LEAD).reconstruction
        assert _instrument(snapshot, PAD).envelopes is _instrument(project, PAD).envelopes
        assert all(
            snapshot.song.channels[name].patterns[index] is pattern
            for name, channel in project.song.channels.items()
            for index, pattern in channel.patterns.items()
        )

    def test_the_shells_are_its_own(self, project: Project) -> None:
        snapshot = project.snapshot()

        assert snapshot.voices is not project.voices
        assert _sample(snapshot, LEAD) is not _sample(project, LEAD)
        assert _sample(snapshot, LEAD).id == _sample(project, LEAD).id
        assert snapshot.song.order is not project.song.order
        assert snapshot.song.order[0] is not project.song.order[0]
        assert snapshot.song.channels[ChannelName.PULSE1] is not project.song.channels[ChannelName.PULSE1]


class TestAnEditOwnsWhatItReplaced:
    """An edit replaces one value, and every value it leaves alone stays the very object the snapshot holds."""

    def test_a_row_edit_owns_one_pattern(self, project: Project) -> None:
        snapshot = project.snapshot()
        channel = project.song.channels[ChannelName.PULSE1]

        channel.set_row(FIRST_PATTERN, EDITED_ROW, Row(volume=1))

        held = snapshot.song.channels[ChannelName.PULSE1]
        assert channel.patterns[FIRST_PATTERN] is not held.patterns[FIRST_PATTERN]
        assert channel.patterns[SECOND_PATTERN] is held.patterns[SECOND_PATTERN]
        unchanged = [index for index in range(len(held.patterns[FIRST_PATTERN].rows)) if index != EDITED_ROW]
        assert all(
            channel.patterns[FIRST_PATTERN].rows[index] is held.patterns[FIRST_PATTERN].rows[index]
            for index in unchanged
        )

    def test_a_resize_shares_every_row_it_keeps(self, project: Project) -> None:
        snapshot = project.snapshot()

        project.song.resize_patterns(SHORTER)

        before = snapshot.song.channels[ChannelName.PULSE1].patterns[FIRST_PATTERN]
        after = project.song.channels[ChannelName.PULSE1].patterns[FIRST_PATTERN]
        assert len(after.rows) == SHORTER
        assert all(left is right for left, right in zip(after.rows, before.rows))

    def test_a_removed_voice_rewrites_only_the_patterns_naming_it(self, project: Project) -> None:
        snapshot = project.snapshot()
        pad = _instrument(project, PAD)

        project.song.clear_voice_references(pad.id)

        before = snapshot.song.channels
        after = project.song.channels
        assert (
            after[ChannelName.TRIANGLE].patterns[FIRST_PATTERN] is before[ChannelName.TRIANGLE].patterns[FIRST_PATTERN]
        )
        assert (
            after[ChannelName.PULSE1].patterns[FIRST_PATTERN] is not before[ChannelName.PULSE1].patterns[FIRST_PATTERN]
        )

    def test_an_envelope_edit_shares_every_other_envelope(self, project: Project) -> None:
        pad = _instrument(project, PAD)
        before = pad.envelopes

        after = before.with_envelope(FeatureKey.VOLUME, EDITED_VOLUME)

        assert after.arpeggio is before.arpeggio
        assert after.volume is not before.volume
