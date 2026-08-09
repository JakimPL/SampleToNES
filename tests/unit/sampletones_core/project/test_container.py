import json
import zipfile
from pathlib import Path
from unittest.mock import patch

import pytest

from sampletones_core.constants.enums import GeneratorName
from sampletones_core.data import Metadata
from sampletones_core.project.container import ProjectContainer
from sampletones_core.project.instruments.instrument import Instrument
from sampletones_core.project.instruments.sample import Sample
from sampletones_core.project.patterns.row import Row
from sampletones_core.project.project import Project
from sampletones_shared.application import SAMPLETONES_PROJECT_DATA_VERSION
from sampletones_shared.constants.project import (
    PROJECT_DOCUMENT_NAME,
    RECONSTRUCTIONS_DIRECTORY,
)
from sampletones_shared.exceptions import (
    IncompatibleProjectVersionError,
    IncorrectReconstructionDataError,
    InvalidProjectDataValuesError,
    MissingProjectDataFileError,
    NotAValidArchiveError,
    UnhandledProjectError,
)
from tests.conftest import ReconstructionFactory
from tests.suite.errors import DIRECTORY_READ_ERRORS


def _rewrite_format_version(source: Path, target: Path, *, format_version: str) -> None:
    with zipfile.ZipFile(source, "r") as archive:
        members = {name: archive.read(name) for name in archive.namelist()}

    document = json.loads(members[PROJECT_DOCUMENT_NAME].decode("utf-8"))
    document["format_version"] = format_version
    members[PROJECT_DOCUMENT_NAME] = json.dumps(document).encode("utf-8")

    with zipfile.ZipFile(target, "w") as archive:
        for name, data in members.items():
            archive.writestr(name, data)


def _populated_project(
    reconstruction_factory: ReconstructionFactory,
    shared: bool = False,
) -> Project:
    project = Project.create(title="Demo")
    project.settings.tempo = 128

    first = Sample(name="lead", reconstruction=reconstruction_factory())
    second_reconstruction = first.reconstruction if shared else reconstruction_factory()
    second = Sample(name="bass", reconstruction=second_reconstruction)
    project.samples.extend([first, second])

    song = project.song
    channel = song[GeneratorName.PULSE1]
    pattern = channel.patterns[0]
    pattern.name = "intro"
    pattern.rows[0] = Row(
        transpose=0,
        command=Instrument(
            sample_id=first.id,
            generator_name=GeneratorName.PULSE1,
        ),
        volume=15,
    )

    extra_index = channel.add_pattern(song.rows_per_pattern, name="verse")
    song.append_frame()
    song.set_order_entry(1, GeneratorName.PULSE1, extra_index)
    song.append_frame()
    song.set_order_entry(2, GeneratorName.PULSE1, 0)
    return project


class TestRoundTrip:
    def test_full_round_trip(
        self,
        tmp_path: Path,
        reconstruction_factory: ReconstructionFactory,
    ) -> None:
        project = _populated_project(reconstruction_factory)
        path = tmp_path / "demo.stp"

        ProjectContainer.save(project, path)
        loaded = ProjectContainer.load(path)

        assert loaded.metadata == project.metadata
        assert loaded.info.title == project.info.title
        assert loaded.settings.tempo == 128
        assert [sample.id for sample in loaded.samples] == [sample.id for sample in project.samples]
        assert [sample.name for sample in loaded.samples] == ["lead", "bass"]

        loaded_song = loaded.song
        assert loaded_song.order == project.song.order
        pulse1_index_at_0 = loaded_song.order[0].get(GeneratorName.PULSE1)
        first_pattern = loaded_song.pattern(
            GeneratorName.PULSE1,
            pulse1_index_at_0,
        )
        assert first_pattern.name == "intro"
        row = first_pattern.rows[0]
        assert row.transpose == 0
        assert row.command is not None
        assert row.command.sample_id == loaded.samples[0].id

    def test_references_resolve_after_load(
        self,
        tmp_path: Path,
        reconstruction_factory: ReconstructionFactory,
    ) -> None:
        project = _populated_project(reconstruction_factory)
        path = tmp_path / "demo.stp"
        ProjectContainer.save(project, path)

        loaded = ProjectContainer.load(path)
        loaded_song = loaded.song
        channel = loaded_song[GeneratorName.PULSE1]
        index_at_0 = loaded_song.order[0].get(GeneratorName.PULSE1)
        row = channel.pattern(index_at_0).rows[0]
        assert loaded.sample(row.command.sample_id) is loaded.samples[0]
        index_at_2 = loaded_song.order[2].get(GeneratorName.PULSE1)
        assert channel.pattern(index_at_0) is channel.pattern(index_at_2)


class TestArchiveLayout:
    def test_unique_reconstructions_are_deduplicated(
        self,
        tmp_path: Path,
        reconstruction_factory: ReconstructionFactory,
    ) -> None:
        project = _populated_project(reconstruction_factory, shared=True)
        path = tmp_path / "demo.stp"
        ProjectContainer.save(project, path)

        with zipfile.ZipFile(path, "r") as archive:
            reconstruction_files = [
                name for name in archive.namelist() if name.startswith(f"{RECONSTRUCTIONS_DIRECTORY}/")
            ]

        assert len(reconstruction_files) == 1

    def test_separate_reconstructions_are_kept(
        self,
        tmp_path: Path,
        reconstruction_factory: ReconstructionFactory,
    ) -> None:
        project = _populated_project(reconstruction_factory, shared=False)
        path = tmp_path / "demo.stp"
        ProjectContainer.save(project, path)

        with zipfile.ZipFile(path, "r") as archive:
            reconstruction_files = [
                name for name in archive.namelist() if name.startswith(f"{RECONSTRUCTIONS_DIRECTORY}/")
            ]

        assert len(reconstruction_files) == 2

    def test_document_is_plain_json(
        self,
        tmp_path: Path,
        reconstruction_factory: ReconstructionFactory,
    ) -> None:
        project = _populated_project(reconstruction_factory)
        path = tmp_path / "demo.stp"
        ProjectContainer.save(project, path)

        with zipfile.ZipFile(path, "r") as archive:
            document = json.loads(archive.read(PROJECT_DOCUMENT_NAME).decode("utf-8"))

        assert document["format_version"] == SAMPLETONES_PROJECT_DATA_VERSION
        assert set(document["song"]["channels"]) == {generator.value for generator in GeneratorName.items()}


class TestEmptyProject:
    def test_round_trip_without_instruments(self, tmp_path: Path) -> None:
        project = Project.create(title="Blank")
        path = tmp_path / "blank.stp"

        ProjectContainer.save(project, path)
        loaded = ProjectContainer.load(path)

        assert len(loaded.samples) == 0
        assert set(loaded.song.channels) == set(GeneratorName.items())

        with zipfile.ZipFile(path, "r") as archive:
            assert all(not name.startswith(f"{RECONSTRUCTIONS_DIRECTORY}/") for name in archive.namelist())


class TestLoadRejectsInvalidArchives:
    def test_missing_file_raises_file_not_found(
        self,
        tmp_path: Path,
    ) -> None:
        with pytest.raises(FileNotFoundError):
            ProjectContainer.load(tmp_path / "nope.stp")

    def test_directory_raises_directory_read_error(
        self,
        tmp_path: Path,
    ) -> None:
        with pytest.raises(DIRECTORY_READ_ERRORS):
            ProjectContainer.load(tmp_path)

    def test_non_zip_raises_not_a_valid_archive(
        self,
        tmp_path: Path,
    ) -> None:
        path = tmp_path / "broken.stp"
        path.write_bytes(b"this is not a zip archive")

        with pytest.raises(NotAValidArchiveError):
            ProjectContainer.load(path)

    def test_missing_document_raises_missing_data_file(
        self,
        tmp_path: Path,
    ) -> None:
        path = tmp_path / "nodoc.stp"
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr("other.txt", "hello")

        with pytest.raises(MissingProjectDataFileError):
            ProjectContainer.load(path)

    def test_malformed_document_raises_invalid_values(
        self,
        tmp_path: Path,
    ) -> None:
        path = tmp_path / "baddoc.stp"
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr(PROJECT_DOCUMENT_NAME, b"{ not valid json")

        with pytest.raises(InvalidProjectDataValuesError):
            ProjectContainer.load(path)

    def test_corrupt_reconstruction_raises_incorrect_data(
        self,
        tmp_path: Path,
        reconstruction_factory: ReconstructionFactory,
    ) -> None:
        project = _populated_project(reconstruction_factory)
        path = tmp_path / "demo.stp"
        ProjectContainer.save(project, path)

        with zipfile.ZipFile(path, "a") as archive:
            archive.writestr(f"{RECONSTRUCTIONS_DIRECTORY}/corrupt.stn", b"garbage-not-a-flatbuffer")

        with pytest.raises(IncorrectReconstructionDataError):
            ProjectContainer.load(path)

    def test_missing_reconstruction_reference_raises_missing_data_file(
        self,
        tmp_path: Path,
        reconstruction_factory: ReconstructionFactory,
    ) -> None:
        project = _populated_project(reconstruction_factory)
        full = tmp_path / "demo.stp"
        ProjectContainer.save(project, full)

        stripped = tmp_path / "stripped.stp"
        with zipfile.ZipFile(full, "r") as source:
            document = source.read(PROJECT_DOCUMENT_NAME)
        with zipfile.ZipFile(stripped, "w") as target:
            target.writestr(PROJECT_DOCUMENT_NAME, document)

        with pytest.raises(MissingProjectDataFileError):
            ProjectContainer.load(stripped)

    def test_unexpected_error_wrapped_as_unhandled(
        self,
        tmp_path: Path,
    ) -> None:
        path = tmp_path / "demo.stp"
        ProjectContainer.save(Project.create(title="Demo"), path)

        with patch.object(
            ProjectContainer,
            "_build_project",
            side_effect=RuntimeError("runtime_error"),
        ):
            with pytest.raises(UnhandledProjectError):
                ProjectContainer.load(path)


class TestVersionCompatibility:
    def test_incompatible_format_version_raises(
        self,
        tmp_path: Path,
        reconstruction_factory: ReconstructionFactory,
    ) -> None:
        project = _populated_project(reconstruction_factory)
        original = tmp_path / "demo.stp"
        ProjectContainer.save(project, original)
        bumped = tmp_path / "bumped.stp"
        _rewrite_format_version(original, bumped, format_version="9.0")

        with pytest.raises(IncompatibleProjectVersionError) as exc_info:
            ProjectContainer.load(bumped)

        assert exc_info.value.expected_version == SAMPLETONES_PROJECT_DATA_VERSION
        assert exc_info.value.actual_version == "9.0"

    def test_incompatible_embedded_reconstruction_version_rejected(
        self,
        tmp_path: Path,
        reconstruction_factory: ReconstructionFactory,
    ) -> None:
        """A project carrying a reconstruction from another build is refused as it opens."""
        project = _populated_project(reconstruction_factory)
        project.samples[0].reconstruction = project.samples[0].reconstruction.model_copy(
            update={"metadata": Metadata(reconstruction_data_version="0.0")},
        )
        path = tmp_path / "demo.stp"
        ProjectContainer.save(project, path)

        with pytest.raises(IncorrectReconstructionDataError):
            ProjectContainer.load(path)
