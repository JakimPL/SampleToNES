from typing import Final, List

import pytest

from sampletones_core.compatibility.kind import ObjectKind
from sampletones_core.constants.algorithm import RESTING_STEM_ID
from sampletones_core.constants.enums import ChannelName
from sampletones_core.project.container import ProjectContainer
from sampletones_core.project.patterns.row import Row
from sampletones_core.project.project import Project
from sampletones_core.project.voices.note_off import NoteOff
from sampletones_core.project.voices.note_on import NoteOn
from sampletones_core.project.voices.sample import Sample
from sampletones_shared.application import (
    SAMPLETONES_PROJECT_DATA_VERSION,
    SAMPLETONES_RECONSTRUCTION_DATA_VERSION,
)
from tests.suite.compatibility import PROJECT_VERSION, archived, stored_version

VOICE_NAMES: Final[List[str]] = ["kick", "kick again"]
PATTERN_NAME: Final[str] = "verse"
PATTERN_CHANNEL: Final[ChannelName] = ChannelName.PULSE2
ROWS_PER_PATTERN: Final[int] = 4
PROJECT_TITLE: Final[str] = "Corpus"
PROJECT_AUTHOR: Final[str] = "Archivist"
PROJECT_COMMENT: Final[str] = "A document kept to be read back"
PROJECT_TEMPO: Final[int] = 132
ROW_TRANSPOSE: Final[int] = 3
ROW_VOLUME: Final[int] = 9


@pytest.fixture(name="loaded")
def loaded_fixture() -> Project:
    """The archived project read the way a build opens one."""
    return ProjectContainer.load(archived(ObjectKind.PROJECT, PROJECT_VERSION))


def _rows(project: Project) -> List[Row]:
    pattern = project.song.pattern(PATTERN_CHANNEL, 0)
    assert pattern is not None
    return pattern.rows


class TestTheVersionAnUpgradedProjectOpensFrom:
    """A document states its version at the root, which the load contract reads and then spends."""

    def test_the_archived_document_stands_at_an_older_version(self) -> None:
        path = archived(ObjectKind.PROJECT, PROJECT_VERSION)

        assert stored_version(ObjectKind.PROJECT, path) == PROJECT_VERSION
        assert PROJECT_VERSION != SAMPLETONES_PROJECT_DATA_VERSION

    def test_it_opens_all_the_same(self, loaded: Project) -> None:
        """The contract refuses a version no chain reaches, so opening is the chain having run."""
        assert loaded.voices


class TestTheVoicesAnUpgradedProjectHolds:
    """What a 1.0 document called its samples are the voices a project holds now."""

    def test_every_sample_reads_as_a_voice(self, loaded: Project) -> None:
        assert [voice.name for voice in loaded.voices] == VOICE_NAMES
        assert all(isinstance(voice, Sample) for voice in loaded.voices)

    def test_the_voices_share_one_reconstruction(self, loaded: Project) -> None:
        """A document stores a reconstruction once however many voices name it."""
        assert len({id(voice.reconstruction) for voice in loaded.voices}) == 1


class TestTheArrangementAnUpgradedProjectKeeps:
    """The order, the patterns and every note column a row holds stand as they were written."""

    def test_the_song_keeps_its_shape(self, loaded: Project) -> None:
        assert loaded.song.rows_per_pattern == ROWS_PER_PATTERN
        assert loaded.song.order_length() == 1

    def test_the_pattern_keeps_the_name_it_was_given(self, loaded: Project) -> None:
        pattern = loaded.song.pattern(PATTERN_CHANNEL, 0)

        assert pattern is not None
        assert pattern.name == PATTERN_NAME

    def test_a_row_naming_a_sample_reads_as_a_note_on(self, loaded: Project) -> None:
        """A 1.0 row named a sample and a generator, which the step reads as the voice to start."""
        command = _rows(loaded)[0].command

        assert isinstance(command, NoteOn)
        assert command.voice_id == loaded.voices[0].id

    def test_a_row_carries_the_columns_beside_its_note(self, loaded: Project) -> None:
        row = _rows(loaded)[1]

        assert isinstance(row.command, NoteOn)
        assert row.command.voice_id == loaded.voices[1].id
        assert row.transpose == ROW_TRANSPOSE
        assert row.volume == ROW_VOLUME

    def test_a_row_letting_a_note_go_reads_as_one(self, loaded: Project) -> None:
        assert isinstance(_rows(loaded)[2].command, NoteOff)

    def test_a_row_holding_nothing_stands_empty(self, loaded: Project) -> None:
        assert _rows(loaded)[3].is_empty()


class TestWhatAnUpgradedProjectSaysOfItself:
    def test_it_keeps_what_it_was_named(self, loaded: Project) -> None:
        assert loaded.info.title == PROJECT_TITLE
        assert loaded.info.author == PROJECT_AUTHOR
        assert loaded.info.comment == PROJECT_COMMENT

    def test_it_keeps_the_tempo_it_plays_at(self, loaded: Project) -> None:
        assert loaded.settings.tempo == PROJECT_TEMPO


class TestTheReconstructionAnUpgradedProjectCarries:
    """A project carries its reconstructions through the same chain a stored file travels."""

    def test_the_embedded_reconstruction_states_the_version_this_build_reads(self, loaded: Project) -> None:
        reconstruction = loaded.voices[0].reconstruction

        assert reconstruction.metadata.reconstruction_data_version == SAMPLETONES_RECONSTRUCTION_DATA_VERSION

    def test_it_sounds_the_channel_it_was_written_with(self, loaded: Project) -> None:
        reconstruction = loaded.voices[0].reconstruction

        assert frozenset(reconstruction.playing_channels) == frozenset({PATTERN_CHANNEL})

    def test_a_silent_frame_answers_to_rest(self, loaded: Project) -> None:
        reconstruction = loaded.voices[0].reconstruction
        owners = reconstruction.stems_data.assignments_by_channel[PATTERN_CHANNEL]
        stream = reconstruction.instructions[PATTERN_CHANNEL]

        assert [owner == RESTING_STEM_ID for owner in owners] == [not item.on for item in stream]
