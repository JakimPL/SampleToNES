import json
import zipfile
from pathlib import Path
from typing import Any, Callable, Dict, Final, Tuple
from unittest.mock import patch

import pytest

from sampletones_core.constants.enums import ChannelName
from sampletones_core.data import Metadata
from sampletones_core.features.envelope import Envelope
from sampletones_core.instructions import PulseInstruction
from sampletones_core.project.container import ProjectContainer
from sampletones_core.project.patterns.pitch import Step
from sampletones_core.project.patterns.row import Row
from sampletones_core.project.project import Project
from sampletones_core.project.voices.envelopes import InstrumentEnvelopes
from sampletones_core.project.voices.instrument import Instrument
from sampletones_core.project.voices.note_on import NoteOn
from sampletones_core.project.voices.sample import Sample
from sampletones_core.reconstructions import Reconstruction
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
from tests.suite.stems import SHARED_CHANNEL, taking_turns_reconstruction

Document = Dict[str, Any]
DocumentRewrite = Callable[[Document], Document]

UNREACHED_VERSION: Final[str] = "9.0"
SHARING_SOURCES: Final[Tuple[Path, Path]] = (Path("a.wav"), Path("b.wav"))
ARCHIVE_NAME: Final[str] = "shared.stp"
EDITED: Final[PulseInstruction] = PulseInstruction(on=True, pitch=67, volume=11, duty_cycle=1)
EDITED_PITCH: Final[int] = 67


def _rewrite_format_version(source: Path, target: Path, *, format_version: str) -> None:
    with zipfile.ZipFile(source, "r") as archive:
        members = {name: archive.read(name) for name in archive.namelist()}

    document = json.loads(members[PROJECT_DOCUMENT_NAME].decode("utf-8"))
    document["format_version"] = format_version
    members[PROJECT_DOCUMENT_NAME] = json.dumps(document).encode("utf-8")

    with zipfile.ZipFile(target, "w") as archive:
        for name, data in members.items():
            archive.writestr(name, data)


def _rewrite_document(source: Path, target: Path, rewrite: DocumentRewrite) -> None:
    with zipfile.ZipFile(source, "r") as archive:
        members = {name: archive.read(name) for name in archive.namelist()}

    document = json.loads(members[PROJECT_DOCUMENT_NAME].decode("utf-8"))
    members[PROJECT_DOCUMENT_NAME] = json.dumps(rewrite(document)).encode("utf-8")

    with zipfile.ZipFile(target, "w") as archive:
        for name, data in members.items():
            archive.writestr(name, data)


def _another_builds_document(document: Document) -> Document:
    """The document as a build no step reaches might write it: another version and a song it calls otherwise."""
    reshaped = {key: value for key, value in document.items() if key != "song"}
    return {**reshaped, "format_version": UNREACHED_VERSION, "arrangement": document["song"]}


def _populated_project(
    reconstruction_factory: ReconstructionFactory,
    shared: bool = False,
) -> Project:
    project = Project.create(title="Demo")
    project.settings.tempo = 128

    first = Sample(name="lead", reconstruction=reconstruction_factory())
    second_reconstruction = first.reconstruction if shared else reconstruction_factory()
    second = Sample(name="bass", reconstruction=second_reconstruction)
    project.voices.extend([first, second])

    song = project.song
    channel = song[ChannelName.PULSE1]
    pattern = channel.patterns[0]
    pattern.name = "intro"
    pattern.rows[0] = Row(
        pitch=Step(value=0),
        command=NoteOn(voice_id=first.id),
        volume=15,
    )

    extra_index = channel.add_pattern(song.rows_per_pattern, name="verse")
    song.append_frame()
    song.set_order_entry(1, ChannelName.PULSE1, extra_index)
    song.append_frame()
    song.set_order_entry(2, ChannelName.PULSE1, 0)
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
        assert [sample.id for sample in loaded.voices] == [sample.id for sample in project.voices]
        assert [sample.name for sample in loaded.voices] == ["lead", "bass"]

        loaded_song = loaded.song
        assert loaded_song.order == project.song.order
        pulse1_index_at_0 = loaded_song.order[0].get(ChannelName.PULSE1)
        first_pattern = loaded_song.pattern(
            ChannelName.PULSE1,
            pulse1_index_at_0,
        )
        assert first_pattern.name == "intro"
        row = first_pattern.rows[0]
        assert row.pitch == Step(value=0)
        assert row.command is not None
        assert row.command.voice_id == loaded.voices[0].id

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
        channel = loaded_song[ChannelName.PULSE1]
        index_at_0 = loaded_song.order[0].get(ChannelName.PULSE1)
        row = channel.pattern(index_at_0).rows[0]
        assert loaded.voice(row.command.voice_id) is loaded.voices[0]
        index_at_2 = loaded_song.order[2].get(ChannelName.PULSE1)
        assert channel.pattern(index_at_0) is channel.pattern(index_at_2)


class TestInstrumentsRoundTrip:
    """An instrument carries no payload beside itself, so a project holds it whole in its document."""

    def test_an_instrument_survives_a_round_trip(self, tmp_path: Path) -> None:
        project = Project.create(title="Demo")
        instrument = Instrument(
            name="lead",
            envelopes=InstrumentEnvelopes(
                volume=Envelope(items=(15, 12), loop_point=0),
                arpeggio=Envelope(items=(0, 7)),
                duty_cycle=Envelope(items=(2,)),
            ),
            initial_pitch=55,
            initial_period=3,
        )
        project.voices.append(instrument)
        path = tmp_path / "demo.stp"

        ProjectContainer.save(project, path)
        loaded = ProjectContainer.load(path)

        assert loaded.voices[0] == instrument
        restored = loaded.voice(instrument.id)
        assert isinstance(restored, Instrument)
        assert restored.envelopes == instrument.envelopes
        assert restored.initial_pitch == instrument.initial_pitch
        assert restored.initial_period == instrument.initial_period
        assert restored.envelopes.volume.loop_point == instrument.envelopes.volume.loop_point

    def test_an_instrument_leaves_no_reconstruction_in_the_archive(self, tmp_path: Path) -> None:
        project = Project.create(title="Demo")
        project.voices.append(Instrument(name="lead"))
        path = tmp_path / "demo.stp"

        ProjectContainer.save(project, path)

        with zipfile.ZipFile(path) as archive:
            assert [name for name in archive.namelist() if name.startswith(RECONSTRUCTIONS_DIRECTORY)] == []

    def test_both_kinds_share_one_pool_in_their_written_order(
        self,
        tmp_path: Path,
        reconstruction_factory: ReconstructionFactory,
    ) -> None:
        project = Project.create(title="Demo")
        sample = Sample(name="bass", reconstruction=reconstruction_factory())
        instrument = Instrument(name="lead")
        project.voices.extend([sample, instrument])
        path = tmp_path / "demo.stp"

        ProjectContainer.save(project, path)
        loaded = ProjectContainer.load(path)

        assert [voice.id for voice in loaded.voices] == [sample.id, instrument.id]
        assert isinstance(loaded.voices[0], Sample)
        assert isinstance(loaded.voices[1], Instrument)

    def test_a_row_naming_an_instrument_still_names_it_after_a_round_trip(
        self,
        tmp_path: Path,
    ) -> None:
        project = Project.create(title="Demo")
        instrument = Instrument(name="lead", envelopes=InstrumentEnvelopes(volume=Envelope(items=(15,))))
        project.voices.append(instrument)
        project.song[ChannelName.PULSE1].patterns[0].rows[0] = Row(command=NoteOn(voice_id=instrument.id))
        path = tmp_path / "demo.stp"

        ProjectContainer.save(project, path)
        loaded = ProjectContainer.load(path)

        row = loaded.song[ChannelName.PULSE1].patterns[0].rows[0]
        assert row.command is not None
        assert loaded.voice(row.command.voice_id) is loaded.voices[0]


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
        assert set(document["song"]["channels"]) == {channel.value for channel in ChannelName.items()}


class TestEmptyProject:
    def test_round_trip_without_instruments(self, tmp_path: Path) -> None:
        project = Project.create(title="Blank")
        path = tmp_path / "blank.stp"

        ProjectContainer.save(project, path)
        loaded = ProjectContainer.load(path)

        assert len(loaded.voices) == 0
        assert set(loaded.song.channels) == set(ChannelName.items())

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

    def test_a_document_that_is_not_text_raises_invalid_values(
        self,
        tmp_path: Path,
    ) -> None:
        path = tmp_path / "binarydoc.stp"
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr(PROJECT_DOCUMENT_NAME, b"\xff\xfe\x00\xd8")

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

    def test_a_version_no_step_reaches_is_refused_before_its_shape_is_read(
        self,
        tmp_path: Path,
        reconstruction_factory: ReconstructionFactory,
    ) -> None:
        """A document at another version keeps another build's shape, so the refusal names the version."""
        original = tmp_path / "demo.stp"
        ProjectContainer.save(_populated_project(reconstruction_factory), original)
        reshaped = tmp_path / "reshaped.stp"
        _rewrite_document(original, reshaped, _another_builds_document)

        with pytest.raises(IncompatibleProjectVersionError) as exc_info:
            ProjectContainer.load(reshaped)

        assert (exc_info.value.actual_version, exc_info.value.expected_version) == (
            UNREACHED_VERSION,
            SAMPLETONES_PROJECT_DATA_VERSION,
        )

    def test_the_same_shape_at_the_current_version_is_refused_for_its_shape(
        self,
        tmp_path: Path,
        reconstruction_factory: ReconstructionFactory,
    ) -> None:
        original = tmp_path / "demo.stp"
        ProjectContainer.save(_populated_project(reconstruction_factory), original)
        reshaped = tmp_path / "reshaped.stp"
        _rewrite_document(
            original,
            reshaped,
            lambda document: {**_another_builds_document(document), "format_version": SAMPLETONES_PROJECT_DATA_VERSION},
        )

        with pytest.raises(InvalidProjectDataValuesError):
            ProjectContainer.load(reshaped)

    def test_a_document_stating_no_version_reads_at_the_current_one(
        self,
        tmp_path: Path,
        reconstruction_factory: ReconstructionFactory,
    ) -> None:
        project = _populated_project(reconstruction_factory)
        original = tmp_path / "demo.stp"
        ProjectContainer.save(project, original)
        unstated = tmp_path / "unstated.stp"
        _rewrite_document(
            original,
            unstated,
            lambda document: {key: value for key, value in document.items() if key != "format_version"},
        )

        loaded = ProjectContainer.load(unstated)

        assert [voice.name for voice in loaded.voices] == [voice.name for voice in project.voices]

    def test_incompatible_embedded_reconstruction_version_rejected(
        self,
        tmp_path: Path,
        reconstruction_factory: ReconstructionFactory,
    ) -> None:
        """A project carrying a reconstruction from another build is refused as it opens."""
        project = _populated_project(reconstruction_factory)
        project.voices[0].reconstruction = project.voices[0].reconstruction.model_copy(
            update={"metadata": Metadata(reconstruction_data_version="0.0")},
        )
        path = tmp_path / "demo.stp"
        ProjectContainer.save(project, path)

        with pytest.raises(IncorrectReconstructionDataError):
            ProjectContainer.load(path)


class TestTheArchiveStoresEveryDocument:
    """A project file stores every distinct document its samples hold, and one shared document once."""

    @pytest.fixture
    def document(self) -> Reconstruction:
        """Two recordings taking turns on Pulse 1, the second holding Pulse 2 alone, their locations let go."""
        return taking_turns_reconstruction(SHARING_SOURCES).detached()

    @staticmethod
    def _round_trip(project: Project, tmp_path: Path) -> Project:
        path = tmp_path / ARCHIVE_NAME
        ProjectContainer.save(project, path)
        return ProjectContainer.load(path)

    def test_a_shared_document_is_stored_once_and_shared_again(
        self,
        document: Reconstruction,
        tmp_path: Path,
    ) -> None:
        project = Project.create()
        project.voices.append(Sample(name="Lead", reconstruction=document))
        project.voices.append(Sample(name="Twin", reconstruction=document))

        reloaded = TestTheArchiveStoresEveryDocument._round_trip(project, tmp_path)

        first, second = list(reloaded.voices)
        assert isinstance(first, Sample) and isinstance(second, Sample)
        assert first.reconstruction is second.reconstruction

    def test_two_documents_of_one_id_both_survive(
        self,
        document: Reconstruction,
        tmp_path: Path,
    ) -> None:
        edited = document.with_channel_data(
            SHARED_CHANNEL,
            [EDITED, EDITED],
            EDITED_PITCH,
            (),
            heard=document.recorded_stem_ids,
        )
        project = Project.create()
        project.voices.append(Sample(name="Lead", reconstruction=document))
        project.voices.append(Sample(name="Copy", reconstruction=edited))

        reloaded = TestTheArchiveStoresEveryDocument._round_trip(project, tmp_path)

        first, second = list(reloaded.voices)
        assert isinstance(first, Sample) and isinstance(second, Sample)
        assert first.reconstruction.instructions[SHARED_CHANNEL] == document.instructions[SHARED_CHANNEL]
        assert second.reconstruction.instructions[SHARED_CHANNEL] == edited.instructions[SHARED_CHANNEL]
