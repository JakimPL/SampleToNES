from pathlib import Path
from typing import Final

import pytest

from sampletones_core.compatibility.kind import ObjectKind
from sampletones_core.constants.algorithm import RESTING_STEM_ID
from sampletones_core.constants.enums import ChannelName, SpectrumMethod
from sampletones_core.library.data import InstructionLibraryData
from sampletones_core.project.container import ProjectContainer
from sampletones_core.reconstructions import Reconstruction
from sampletones_shared.application import (
    SAMPLETONES_LIBRARY_DATA_VERSION,
    SAMPLETONES_PROJECT_DATA_VERSION,
    SAMPLETONES_RECONSTRUCTION_DATA_VERSION,
)
from sampletones_tools.compatibility.documents import SOURCE_PATH, library_tones
from sampletones_tools.compatibility.paths import archived_path, version_part
from sampletones_tools.compatibility.writer import archive

CORPUS_FORMATS: Final[int] = 3


@pytest.fixture(name="corpus")
def corpus_fixture(tmp_path: Path) -> Path:
    """A corpus this build has just written, which is what a release archives."""
    archive(tmp_path)
    return tmp_path


class TestTheSpellingAVersionTakes:
    """A file is named after the data version it was written at, as the step modules are."""

    def test_a_version_reads_as_the_step_modules_spell_one(self) -> None:
        assert version_part("2.1") == "v2_1"

    def test_a_format_keeps_its_files_apart_from_another_s(self) -> None:
        reconstruction = archived_path(ObjectKind.RECONSTRUCTION, "2.1", Path("corpus"))
        library = archived_path(ObjectKind.LIBRARY, "2.1", Path("corpus"))

        assert reconstruction != library
        assert reconstruction.parent.name == ObjectKind.RECONSTRUCTION.value


class TestWhatTheCorpusIsWrittenWith:
    """Archiving writes one document per format at the versions this build states."""

    def test_every_format_answers_with_a_file(self, corpus: Path) -> None:
        written = sorted(path for path in corpus.rglob("*") if path.is_file())

        assert len(written) == CORPUS_FORMATS

    def test_each_file_stands_where_its_version_names(self, corpus: Path) -> None:
        for kind, version in (
            (ObjectKind.RECONSTRUCTION, SAMPLETONES_RECONSTRUCTION_DATA_VERSION),
            (ObjectKind.LIBRARY, SAMPLETONES_LIBRARY_DATA_VERSION),
            (ObjectKind.PROJECT, SAMPLETONES_PROJECT_DATA_VERSION),
        ):
            assert archived_path(kind, version, corpus).is_file()

    def test_a_version_already_archived_stands_as_it_was_written(self, corpus: Path) -> None:
        path = archived_path(ObjectKind.RECONSTRUCTION, SAMPLETONES_RECONSTRUCTION_DATA_VERSION, corpus)
        written = path.read_bytes()

        assert archive(corpus) == []
        assert path.read_bytes() == written

    def test_a_deliberate_replacement_writes_it_again(self, corpus: Path) -> None:
        assert len(archive(corpus, force=True)) == CORPUS_FORMATS


class TestWhatAnArchivedReconstructionStates:
    """The archived reconstruction names every channel, its recording, and one owner per frame."""

    @staticmethod
    def _loaded(corpus: Path) -> Reconstruction:
        path = archived_path(ObjectKind.RECONSTRUCTION, SAMPLETONES_RECONSTRUCTION_DATA_VERSION, corpus)
        return Reconstruction.load(path, fast=False)

    def test_every_channel_sounds(self, corpus: Path) -> None:
        assert frozenset(self._loaded(corpus).playing_channels) == frozenset(ChannelName.items())

    def test_a_silent_frame_answers_to_rest(self, corpus: Path) -> None:
        """A record naming a recording on a silent frame is what the archived file must not carry."""
        loaded = self._loaded(corpus)
        for channel_name, stem_ids in loaded.stems_data.assignments_by_channel.items():
            stream = loaded.instructions[channel_name]
            assert [stem_id == RESTING_STEM_ID for stem_id in stem_ids] == [not item.on for item in stream]

    def test_a_channel_stands_silent_somewhere(self, corpus: Path) -> None:
        """The rule above says nothing unless a silent frame is actually stored."""
        loaded = self._loaded(corpus)
        assert any(RESTING_STEM_ID in stem_ids for stem_ids in loaded.stems_data.assignments_by_channel.values())

    def test_the_recording_it_was_built_from_is_named(self, corpus: Path) -> None:
        assert self._loaded(corpus).audio_filepath == (SOURCE_PATH,)


class TestWhatAnArchivedLibraryStates:
    """The archived library is measured the way the step carrying one forward has work to do."""

    @staticmethod
    def _loaded(corpus: Path) -> InstructionLibraryData:
        path = archived_path(ObjectKind.LIBRARY, SAMPLETONES_LIBRARY_DATA_VERSION, corpus)
        return InstructionLibraryData.load(path, fast=False)

    def test_it_is_measured_by_a_windowed_transform(self, corpus: Path) -> None:
        config = self._loaded(corpus).config

        assert config.spectrum_method is SpectrumMethod.FFT
        assert config.transformation_gamma > 0

    def test_every_tone_it_was_given_is_stored(self, corpus: Path) -> None:
        stored = self._loaded(corpus).data

        assert all(instruction in stored for instruction in library_tones())


class TestWhatAnArchivedProjectStates:
    """The archived project keeps one copy of the reconstruction its voices share."""

    @staticmethod
    def _loaded(corpus: Path) -> object:
        path = archived_path(ObjectKind.PROJECT, SAMPLETONES_PROJECT_DATA_VERSION, corpus)
        return ProjectContainer.load(path)

    def test_two_voices_share_one_reconstruction(self, corpus: Path) -> None:
        project = self._loaded(corpus)
        voices = list(project.voices)  # type: ignore[attr-defined]

        assert len(voices) == 2
        assert len({id(voice.reconstruction) for voice in voices}) == 1
