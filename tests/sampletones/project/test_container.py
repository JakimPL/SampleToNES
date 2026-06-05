import json
import zipfile
from pathlib import Path

from sampletones_core.constants.enums import GeneratorName
from sampletones_core.project.container import ProjectContainer
from sampletones_core.project.instruments.instrument import Instrument
from sampletones_core.project.instruments.sample import Sample
from sampletones_core.project.patterns.pattern import Pattern
from sampletones_core.project.patterns.row import Row
from sampletones_core.project.project import Project
from sampletones_shared.constants.project import (
    PROJECT_DOCUMENT_NAME,
    RECONSTRUCTIONS_DIRECTORY,
)


def _populated_project(reconstruction_factory, shared: bool = False) -> Project:
    project = Project.create(title="Demo")
    project.settings.tempo = 128

    first = Sample(name="lead", reconstruction=reconstruction_factory())
    second_reconstruction = first.reconstruction if shared else reconstruction_factory()
    second = Sample(name="bass", reconstruction=second_reconstruction)
    project.samples.extend([first, second])

    channel = project.song[GeneratorName.PULSE1]
    pattern = channel.patterns[0]
    pattern.name = "intro"
    pattern.rows[0] = Row(
        transpose=0,
        instrument=Instrument(
            sample_id=first.id,
            generator_name=GeneratorName.PULSE1,
        ),
        volume=15,
    )

    extra = Pattern.empty(project.settings.rows_per_pattern, name="verse")
    channel.patterns.append(extra)
    channel.order = [pattern.id, extra.id, pattern.id]
    return project


class TestRoundTrip:
    def test_full_round_trip(self, tmp_path: Path, reconstruction_factory) -> None:
        project = _populated_project(reconstruction_factory)
        path = tmp_path / "demo.stp"

        ProjectContainer.save(project, path)
        loaded = ProjectContainer.load(path)

        assert loaded.metadata == project.metadata
        assert loaded.info.title == project.info.title
        assert loaded.settings.tempo == 128
        assert [sample.id for sample in loaded.samples] == [sample.id for sample in project.samples]
        assert [sample.name for sample in loaded.samples] == ["lead", "bass"]

        channel = loaded.song[GeneratorName.PULSE1]
        assert channel.order == project.song[GeneratorName.PULSE1].order
        first_pattern = channel.pattern(channel.order[0])
        assert first_pattern.name == "intro"
        row = first_pattern.rows[0]
        assert row.transpose == 0
        assert row.instrument is not None
        assert row.instrument.sample_id == loaded.samples[0].id

    def test_references_resolve_after_load(self, tmp_path: Path, reconstruction_factory) -> None:
        project = _populated_project(reconstruction_factory)
        path = tmp_path / "demo.stp"
        ProjectContainer.save(project, path)

        loaded = ProjectContainer.load(path)
        channel = loaded.song[GeneratorName.PULSE1]
        row = channel.pattern(channel.order[0]).rows[0]
        assert loaded.sample(row.instrument.sample_id) is loaded.samples[0]
        # the order referenc`es the same pattern twice; both resolve to one object
        assert channel.pattern(channel.order[0]) is channel.pattern(channel.order[2])


class TestArchiveLayout:
    def test_unique_reconstructions_are_deduplicated(self, tmp_path: Path, reconstruction_factory) -> None:
        project = _populated_project(reconstruction_factory, shared=True)
        path = tmp_path / "demo.stp"
        ProjectContainer.save(project, path)

        with zipfile.ZipFile(path, "r") as archive:
            reconstruction_files = [
                name for name in archive.namelist() if name.startswith(f"{RECONSTRUCTIONS_DIRECTORY}/")
            ]

        assert len(reconstruction_files) == 1

    def test_separate_reconstructions_are_kept(self, tmp_path: Path, reconstruction_factory) -> None:
        project = _populated_project(reconstruction_factory, shared=False)
        path = tmp_path / "demo.stp"
        ProjectContainer.save(project, path)

        with zipfile.ZipFile(path, "r") as archive:
            reconstruction_files = [
                name for name in archive.namelist() if name.startswith(f"{RECONSTRUCTIONS_DIRECTORY}/")
            ]

        assert len(reconstruction_files) == 2

    def test_document_is_plain_json(self, tmp_path: Path, reconstruction_factory) -> None:
        project = _populated_project(reconstruction_factory)
        path = tmp_path / "demo.stp"
        ProjectContainer.save(project, path)

        with zipfile.ZipFile(path, "r") as archive:
            document = json.loads(archive.read(PROJECT_DOCUMENT_NAME).decode("utf-8"))

        assert document["format_version"] == "1.0"
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
