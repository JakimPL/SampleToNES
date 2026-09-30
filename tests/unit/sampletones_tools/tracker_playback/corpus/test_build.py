from typing import Final

import pytest

from sampletones_core.constants.enums import ChannelName
from sampletones_core.formats.bitphase.builder import build_bitphase
from sampletones_core.project.project import Project
from sampletones_core.project.voices.note_on import NoteOn
from sampletones_tools.corpus.build import Corpus
from sampletones_tools.corpus.module import ModuleConfig
from sampletones_tools.corpus.song import ChannelSpec, RowSpec, SongSpec
from sampletones_tools.tracker_playback.corpus import build
from sampletones_tools.tracker_playback.corpus.build import (
    arrangement_project,
    comparison_corpus,
    written_project,
)
from sampletones_tools.tracker_playback.corpus.spec import (
    ArrangementSpec,
    CorpusSpec,
    FrameRun,
    ProjectSpec,
    SampleSpec,
)
from sampletones_tools.tracker_playback.trace.application import application_trace

MODULE: Final = ModuleConfig(title="Tone", author="Someone", tempo=150, speed=6, nes_frequency=60)
TONE: Final = SampleSpec(
    kind="sample",
    channels={
        ChannelName.PULSE1: [
            FrameRun(count=4, frame={"on": True, "pitch": 60, "volume": 15, "duty_cycle": 2}),
        ]
    },
)
PROJECT: Final = ProjectSpec(
    name="tone",
    purpose="A tone.",
    module=MODULE,
    voices=["tone"],
    song=SongSpec(
        rows_per_pattern=2,
        order=[{ChannelName.PULSE1: 0}],
        channels={ChannelName.PULSE1: ChannelSpec(patterns={0: [RowSpec(row=0, voice="tone", volume=12)]})},
    ),
)
ARRANGEMENT: Final = ArrangementSpec(name="arrangement-groove", purpose="The arrangement, faster.", tempo=210)
CORPUS: Final = CorpusSpec(voices={"tone": TONE}, projects=[PROJECT], arrangements=[ARRANGEMENT])


class TestWrittenProject:
    def test_every_shipped_project_builds_exports_and_plays(self) -> None:
        corpus = CorpusSpec.load()

        for spec in corpus.projects:
            project = written_project(spec, corpus).project
            build_bitphase(project)
            assert application_trace(project).ticks > 0, spec.name

    def test_the_project_holds_the_voices_it_lists_and_plays_its_song(self) -> None:
        written = written_project(PROJECT, CORPUS)

        project = written.project
        assert (written.name, written.purpose) == ("tone", "A tone.")
        assert [voice.name for voice in project.voices] == ["tone"]
        row = project.song.channels[ChannelName.PULSE1].patterns[0].rows[0]
        assert row.command == NoteOn(voice_id=project.voices[0].id)
        assert row.volume == 12
        assert (project.settings.tempo, project.settings.speed) == (MODULE.tempo, MODULE.speed)

    def test_each_project_holds_voices_of_its_own(self) -> None:
        first = written_project(PROJECT, CORPUS).project
        second = written_project(PROJECT, CORPUS).project

        assert first.voices[0] is not second.voices[0]

    def test_a_voice_the_corpus_lacks_is_refused(self) -> None:
        with pytest.raises(KeyError, match="lead"):
            written_project(PROJECT.model_copy(update={"voices": ["lead"]}), CORPUS)


class TestArrangementProject:
    def test_the_arrangement_plays_at_the_tempo_the_spec_names(self) -> None:
        arrangement = written_project(PROJECT, CORPUS).project

        played = arrangement_project(ARRANGEMENT, arrangement)

        assert (played.name, played.purpose) == (ARRANGEMENT.name, ARRANGEMENT.purpose)
        assert played.project.settings.tempo == ARRANGEMENT.tempo
        assert arrangement.settings.tempo == MODULE.tempo


class TestComparisonCorpus:
    def test_the_written_projects_come_first_then_the_arrangement_at_each_tempo(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        arrangement: Project = written_project(PROJECT, CORPUS).project
        monkeypatch.setattr(build, "build_synthetic_corpus", lambda: Corpus(catalog={}, project=arrangement))

        projects = comparison_corpus(CORPUS)

        assert [project.name for project in projects] == ["tone", "arrangement-groove"]
        assert projects[1].project.song is arrangement.song
