from pathlib import Path
from typing import Final, Tuple

import numpy as np
import pytest
import soundfile

from assets.demo.paths import CONFIG_FILE, LIBRARY_FOLDER, PROJECTS_FOLDER, RECONSTRUCTIONS_FOLDER, RECORDINGS_FOLDER
from assets.demo.specification import DemoSpecification
from assets.demo.tree import build_demo
from sampletones_core.configs import Config
from sampletones_core.project import ProjectContainer
from sampletones_core.reconstructions import Reconstruction
from sampletones_shared.paths.extensions import EXT_FILE_PROJECT, EXT_FILE_RECONSTRUCTION, EXT_FILE_WAVE

SPECIFICATION: Final[DemoSpecification] = DemoSpecification.load()
AUDIBLE_RMS: Final[float] = 0.01


@pytest.fixture(name="tree", scope="session")
def tree_fixture(tmp_path_factory: pytest.TempPathFactory) -> Tuple[Path, Tuple[Path, ...]]:
    """The demo tree built once for the session, with every file the build reported."""
    destination = tmp_path_factory.mktemp("demo") / "tree"
    return destination, build_demo(destination)


def documents(root: Path) -> Tuple[Path, ...]:
    return tuple(sorted((root / RECONSTRUCTIONS_FOLDER).rglob(f"*{EXT_FILE_RECONSTRUCTION}")))


class TestTheTree:
    """The demo tree holds a documents folder a person can run the application from, with recordings beside it."""

    def test_every_file_reported_stands(self, tree: Tuple[Path, Tuple[Path, ...]]) -> None:
        _, written = tree

        assert written
        assert all(path.is_file() for path in written)

    def test_every_recording_sounds(self, tree: Tuple[Path, Tuple[Path, ...]]) -> None:
        root, _ = tree
        recordings = sorted((root / RECORDINGS_FOLDER).rglob(f"*{EXT_FILE_WAVE}"))
        expected = len(SPECIFICATION.recordings.hits) + len(SPECIFICATION.recordings.piece.stems)

        assert len(recordings) == expected
        for recording in recordings:
            audio, _ = soundfile.read(recording)
            assert float(np.sqrt(np.mean(np.square(audio)))) > AUDIBLE_RMS, recording.name

    def test_the_configuration_names_the_tree_s_own_folders(self, tree: Tuple[Path, Tuple[Path, ...]]) -> None:
        root, _ = tree
        config = Config.load(root / CONFIG_FILE)

        assert config.library_directory == root / LIBRARY_FOLDER
        assert config.output_directory == root / RECONSTRUCTIONS_FOLDER
        assert any((root / LIBRARY_FOLDER).iterdir())

    def test_every_document_names_its_recordings_relative_to_the_tree(
        self, tree: Tuple[Path, Tuple[Path, ...]]
    ) -> None:
        root, _ = tree
        found = documents(root)

        assert len(found) == len(SPECIFICATION.recordings.hits) + 1
        for document in found:
            paths = Reconstruction.load(document).audio_filepath
            assert paths, document.name
            assert all(not path.is_absolute() and (root / path).is_file() for path in paths), document.name

    def test_every_hit_plays_within_the_channels_it_was_given(self, tree: Tuple[Path, Tuple[Path, ...]]) -> None:
        root, _ = tree
        for hit in SPECIFICATION.recordings.hits:
            document = next(path for path in documents(root) if path.stem == hit.name)
            playing = frozenset(Reconstruction.load(document).playing_channels)

            assert playing, hit.name
            assert playing <= frozenset(SPECIFICATION.conversion.hits[hit.name]), hit.name

    def test_the_piece_is_converted_from_every_stem_on_its_own_level(self, tree: Tuple[Path, Tuple[Path, ...]]) -> None:
        root, _ = tree
        piece = SPECIFICATION.recordings.piece
        document = next(path for path in documents(root) if path.stem == piece.name)
        stems_data = Reconstruction.load(document).stems_data

        assert len(stems_data.config.entries) == len(piece.stems)
        assert len(stems_data.config.hierarchy.levels) == len(SPECIFICATION.conversion.piece.levels)
        assert [stems_data.named(entry.id) for entry in stems_data.config.entries] == [
            stem.name for stem in piece.stems
        ]

    def test_the_project_plays_the_hits_and_the_instruments(self, tree: Tuple[Path, Tuple[Path, ...]]) -> None:
        root, _ = tree
        title = SPECIFICATION.project.module.title
        project = ProjectContainer.load(root / PROJECTS_FOLDER / f"{title}{EXT_FILE_PROJECT}")
        names = {voice.name for voice in project.voices}
        expected = {hit.name for hit in SPECIFICATION.recordings.hits} | set(SPECIFICATION.project.instruments)

        assert project.info.title == title
        assert project.info.created == SPECIFICATION.project.created
        assert project.info.modified == SPECIFICATION.project.created
        assert names == expected
        assert len(project.song.order) == len(SPECIFICATION.project.song.order)

    def test_a_folder_holding_files_is_refused(self, tree: Tuple[Path, Tuple[Path, ...]]) -> None:
        root, _ = tree

        with pytest.raises(FileExistsError):
            build_demo(root)
