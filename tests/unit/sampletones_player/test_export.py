import struct
from pathlib import Path
from typing import Final

import pytest

from sampletones_core.constants.enums import ChannelName
from sampletones_core.exports.backend import ExportBackend
from sampletones_core.exports.format import ExportFormat
from sampletones_core.exports.progress import ExportProgress
from sampletones_core.exports.request import (
    InstrumentExport,
    ProjectExport,
    SampleExport,
)
from sampletones_core.exports.scope import ExportScope
from sampletones_core.exports.stage import ExportStage
from sampletones_core.project.project import Project
from sampletones_core.project.settings import ProjectSettings
from sampletones_core.timing import SongTiming
from sampletones_player.builder import SONG_START, song_from_project
from sampletones_player.driver.image import DriverImage
from sampletones_player.export import NSFBackend
from sampletones_player.specification.nsf import (
    ARTIST_OFFSET,
    HEADER_SIZE,
    PROGRAM_SIZE,
    STRING_FIELD_SIZE,
    TITLE_OFFSET,
)
from sampletones_player.specification.song import LOOP_TICK_OFFSET
from sampletones_shared.exceptions import OperationCancelled, SongTooLargeError
from sampletones_shared.paths.extensions import EXT_FILE_NSF
from tests.suite.performance import (
    make_pulse_reconstruction,
    place_instrument,
    project_with_sample,
)
from tests.suite.player import (
    PLAYER_REFERENCE_PITCH,
    player_features,
    player_instrument,
    player_sample,
    varied_features,
)
from tests.suite.progress import RecordingReporter, reported_stages

NTSC_FREQUENCY: Final[int] = 60
SOUNDING_TICKS: Final[int] = 8
BASS_PITCH: Final[int] = 45
OVERLONG_TICKS: Final[int] = 8192
FILENAME: Final[str] = "reconstruction.nsf"
SAMPLE_NAME: Final[str] = "Amen"
PROJECT_TITLE: Final[str] = "Demo"
PROJECT_AUTHOR: Final[str] = "Jakim"
ROWS_PER_PATTERN: Final[int] = 4
WITHDRAWN_WHILE_WALKING: Final[int] = 1
WITHDRAWN_WHILE_COMPRESSING: Final[int] = 2


def lead_slice(name: str, frames: int) -> InstrumentExport:
    return player_instrument(
        name,
        ChannelName.PULSE1,
        player_features(frames, PLAYER_REFERENCE_PITCH, duty_cycle=True),
        nes_frequency=NTSC_FREQUENCY,
        loop=False,
    )


def overlong_sample() -> SampleExport:
    """A reconstruction whose channels turn over at every tick, so its song outgrows the console."""
    return player_sample(
        SAMPLE_NAME,
        (
            player_instrument(
                "lead",
                ChannelName.PULSE1,
                varied_features(OVERLONG_TICKS, PLAYER_REFERENCE_PITCH, duty_cycle=True),
                nes_frequency=NTSC_FREQUENCY,
                loop=False,
            ),
            player_instrument(
                "harmony",
                ChannelName.PULSE2,
                varied_features(OVERLONG_TICKS, PLAYER_REFERENCE_PITCH, duty_cycle=True),
                nes_frequency=NTSC_FREQUENCY,
                loop=False,
            ),
            player_instrument(
                "bass",
                ChannelName.TRIANGLE,
                varied_features(OVERLONG_TICKS, BASS_PITCH, duty_cycle=False),
                nes_frequency=NTSC_FREQUENCY,
                loop=False,
            ),
        ),
        nes_frequency=NTSC_FREQUENCY,
    )


def bass_slice(name: str, frames: int) -> InstrumentExport:
    return player_instrument(
        name,
        ChannelName.TRIANGLE,
        player_features(frames, BASS_PITCH, duty_cycle=False),
        nes_frequency=NTSC_FREQUENCY,
        loop=False,
    )


def written_loop_tick(data: bytes) -> int:
    """The tick a written program comes round to, read out of the song block behind the driver."""
    block = data[HEADER_SIZE + len(DriverImage.load().code) :]
    return int(struct.unpack_from("<H", block, LOOP_TICK_OFFSET)[0])


def read_field(data: bytes, offset: int) -> str:
    return data[offset : offset + STRING_FIELD_SIZE].rstrip(b"\x00").decode()


@pytest.fixture(name="backend")
def backend_fixture() -> NSFBackend:
    return NSFBackend()


class TestSeam:
    """What the backend answers the export seam with."""

    def test_the_backend_writes_the_nsf_format(self, backend: NSFBackend) -> None:
        assert backend.export_format == ExportFormat.NSF

    def test_a_program_plays_every_scope_the_application_exports(self, backend: NSFBackend) -> None:
        assert backend.supported_scopes == frozenset(ExportScope)

    @pytest.mark.parametrize("scope", list(ExportScope))
    def test_every_scope_the_backend_writes_carries_the_nsf_extension(
        self,
        backend: NSFBackend,
        scope: ExportScope,
    ) -> None:
        assert backend.extension(scope) == EXT_FILE_NSF

    def test_the_backend_stands_where_the_seam_expects_one(self, backend: NSFBackend) -> None:
        export_backend: ExportBackend = backend
        assert export_backend.export_format == ExportFormat.NSF


class TestWriteSample:
    """A reconstruction written as one program playing every slice together."""

    def test_the_run_writes_the_destination_alone(self, backend: NSFBackend, tmp_path: Path) -> None:
        destination = tmp_path / FILENAME
        request = player_sample(
            SAMPLE_NAME,
            (lead_slice("lead", SOUNDING_TICKS), bass_slice("bass", SOUNDING_TICKS)),
            nes_frequency=NTSC_FREQUENCY,
        )
        artifact = backend.write_sample(destination, request)
        assert artifact.paths == (destination,)

    def test_the_program_carries_its_driver(self, backend: NSFBackend, tmp_path: Path) -> None:
        destination = tmp_path / FILENAME
        request = player_sample(SAMPLE_NAME, (lead_slice("lead", SOUNDING_TICKS),), nes_frequency=NTSC_FREQUENCY)
        backend.write_sample(destination, request)
        assert len(destination.read_bytes()) > HEADER_SIZE

    def test_the_reconstructions_name_lists_the_program(self, backend: NSFBackend, tmp_path: Path) -> None:
        destination = tmp_path / FILENAME
        request = player_sample(SAMPLE_NAME, (lead_slice("lead", SOUNDING_TICKS),), nes_frequency=NTSC_FREQUENCY)
        backend.write_sample(destination, request)
        assert read_field(destination.read_bytes(), TITLE_OFFSET) == SAMPLE_NAME

    def test_an_export_is_credited_to_nobody(self, backend: NSFBackend, tmp_path: Path) -> None:
        """A reconstruction names no artist, so the field reaches the file empty and a player
        listing the file leaves the line blank.
        """
        destination = tmp_path / FILENAME
        request = player_sample(SAMPLE_NAME, (lead_slice("lead", SOUNDING_TICKS),), nes_frequency=NTSC_FREQUENCY)
        backend.write_sample(destination, request)
        assert read_field(destination.read_bytes(), ARTIST_OFFSET) == ""

    def test_the_envelopes_cross_over_whole(self, backend: NSFBackend, tmp_path: Path) -> None:
        destination = tmp_path / FILENAME
        request = player_sample(SAMPLE_NAME, (lead_slice("lead", SOUNDING_TICKS),), nes_frequency=NTSC_FREQUENCY)
        assert backend.write_sample(destination, request).truncation is None

    def test_a_destination_reaches_a_directory_the_run_creates(self, backend: NSFBackend, tmp_path: Path) -> None:
        destination = tmp_path / "exports" / FILENAME
        request = player_sample(SAMPLE_NAME, (lead_slice("lead", SOUNDING_TICKS),), nes_frequency=NTSC_FREQUENCY)
        backend.write_sample(destination, request)
        assert destination.is_file()

    def test_a_reconstruction_outgrowing_the_program_area_reports_its_size(
        self,
        backend: NSFBackend,
        tmp_path: Path,
    ) -> None:
        destination = tmp_path / FILENAME
        with pytest.raises(SongTooLargeError):
            backend.write_sample(destination, overlong_sample())


class TestWriteInstrument:
    """One channel slice written as a program sounding it alone."""

    def test_the_slice_is_listed_under_its_own_name(self, backend: NSFBackend, tmp_path: Path) -> None:
        destination = tmp_path / FILENAME
        backend.write_instrument(destination, lead_slice("lead", SOUNDING_TICKS))
        assert read_field(destination.read_bytes(), TITLE_OFFSET) == "lead"

    def test_a_slice_plays_the_program_its_reconstruction_would(self, backend: NSFBackend, tmp_path: Path) -> None:
        """A slice sounds on its own channel and the other three rest, which is the reconstruction
        it belongs to with every other slice standing by.
        """
        instrument = lead_slice(SAMPLE_NAME, SOUNDING_TICKS)
        alone = tmp_path / "alone.nsf"
        together = tmp_path / "together.nsf"

        backend.write_instrument(alone, instrument)
        backend.write_sample(together, player_sample(SAMPLE_NAME, (instrument,), nes_frequency=NTSC_FREQUENCY))

        assert alone.read_bytes() == together.read_bytes()


def drum_project() -> Project:
    """A one-frame project sounding a pulse envelope from its first row."""
    project, sample = project_with_sample(
        make_pulse_reconstruction(pitch=PLAYER_REFERENCE_PITCH, count=SOUNDING_TICKS),
        rows_per_pattern=ROWS_PER_PATTERN,
        settings=ProjectSettings(nes_frequency=NTSC_FREQUENCY),
    )
    project.info.title = PROJECT_TITLE
    project.info.author = PROJECT_AUTHOR
    place_instrument(
        project,
        channel_name=ChannelName.PULSE1,
        row_index=0,
        sample=sample,
    )
    return project


class TestWriteProject:
    """A whole composition written as one program the console plays."""

    def test_the_file_is_written(self, backend: NSFBackend, tmp_path: Path) -> None:
        destination = tmp_path / FILENAME
        backend.write_project(destination, ProjectExport(project=drum_project()))
        assert destination.is_file()

    def test_the_program_is_listed_under_the_projects_own_title(
        self,
        backend: NSFBackend,
        tmp_path: Path,
    ) -> None:
        destination = tmp_path / FILENAME
        backend.write_project(destination, ProjectExport(project=drum_project()))
        assert read_field(destination.read_bytes(), TITLE_OFFSET) == PROJECT_TITLE

    def test_the_program_is_credited_to_the_projects_author(
        self,
        backend: NSFBackend,
        tmp_path: Path,
    ) -> None:
        destination = tmp_path / FILENAME
        backend.write_project(destination, ProjectExport(project=drum_project()))
        assert read_field(destination.read_bytes(), ARTIST_OFFSET) == PROJECT_AUTHOR

    def test_the_program_plays_the_song_the_project_arranges(
        self,
        backend: NSFBackend,
        tmp_path: Path,
    ) -> None:
        """What reaches the file is the arrangement, so it lasts the ticks the groove gives it."""
        project = drum_project()
        destination = tmp_path / FILENAME
        backend.write_project(destination, ProjectExport(project=project))
        groove = SongTiming.from_project(project).groove()
        expected = project.song.order_length() * groove.total_ticks
        assert song_from_project(project, SONG_START).ticks == expected

    def test_the_program_repeats_from_its_first_tick(
        self,
        backend: NSFBackend,
        tmp_path: Path,
    ) -> None:
        """A piece of music is listened to over and over, so the file comes round where the
        arrangement ends rather than falling silent there."""
        destination = tmp_path / FILENAME
        backend.write_project(destination, ProjectExport(project=drum_project()))
        assert written_loop_tick(destination.read_bytes()) == SONG_START

    def test_a_destination_reaches_a_directory_the_run_creates(
        self,
        backend: NSFBackend,
        tmp_path: Path,
    ) -> None:
        destination = tmp_path / "exports" / FILENAME
        backend.write_project(destination, ProjectExport(project=drum_project()))
        assert destination.is_file()


class TestWhatAProjectRunSaysAboutItself:
    """A song is played out before it is compressed, and both stages read as they run."""

    def test_the_run_names_each_stage_in_the_order_it_reaches_it(
        self,
        backend: NSFBackend,
        tmp_path: Path,
    ) -> None:
        reporter: RecordingReporter[ExportProgress] = RecordingReporter()
        backend.write_project(tmp_path / FILENAME, ProjectExport(project=drum_project()), reporter)
        assert reported_stages(reporter.reports) == [
            ExportStage.WALKING,
            ExportStage.COMPRESSING,
            ExportStage.WRITING,
        ]

    def test_the_walk_counts_the_ticks_the_song_lasts(
        self,
        backend: NSFBackend,
        tmp_path: Path,
    ) -> None:
        """The groove states the length before a row is played, so the stage travels toward it."""
        project = drum_project()
        reporter: RecordingReporter[ExportProgress] = RecordingReporter()
        backend.write_project(tmp_path / FILENAME, ProjectExport(project=project), reporter)

        walked = [report for report in reporter.reports if report.stage == ExportStage.WALKING]
        groove = SongTiming.from_project(project).groove()
        expected = project.song.order_length() * groove.total_ticks
        assert walked
        assert [report.total for report in walked] == [expected] * len(walked)
        assert walked[-1].completed == expected

    def test_a_withdrawn_walk_leaves_no_file(
        self,
        backend: NSFBackend,
        tmp_path: Path,
    ) -> None:
        destination = tmp_path / FILENAME
        reporter: RecordingReporter[ExportProgress] = RecordingReporter(withdraw_at=WITHDRAWN_WHILE_WALKING)
        with pytest.raises(OperationCancelled):
            backend.write_project(destination, ProjectExport(project=drum_project()), reporter)

        assert reporter.last.stage == ExportStage.WALKING
        assert not destination.exists()


class TestWhatARunSaysAboutItself:
    """A program takes seconds to build, so the run names the work it is doing as it does it."""

    def test_the_run_names_each_stage_in_the_order_it_reaches_it(
        self,
        backend: NSFBackend,
        tmp_path: Path,
    ) -> None:
        reporter: RecordingReporter[ExportProgress] = RecordingReporter()
        request = player_sample(SAMPLE_NAME, (lead_slice("lead", SOUNDING_TICKS),), nes_frequency=NTSC_FREQUENCY)
        backend.write_sample(tmp_path / FILENAME, request, reporter)
        assert reported_stages(reporter.reports) == [
            ExportStage.WALKING,
            ExportStage.COMPRESSING,
            ExportStage.WRITING,
        ]

    def test_the_compression_reports_the_bytes_it_has_laid_down(
        self,
        backend: NSFBackend,
        tmp_path: Path,
    ) -> None:
        """A search ends where the song runs out of phrases that pay, so it counts bytes alone."""
        reporter: RecordingReporter[ExportProgress] = RecordingReporter()
        request = player_sample(SAMPLE_NAME, (lead_slice("lead", SOUNDING_TICKS),), nes_frequency=NTSC_FREQUENCY)
        backend.write_sample(tmp_path / FILENAME, request, reporter)
        compressing = [report for report in reporter.reports if report.stage == ExportStage.COMPRESSING]
        assert compressing and all(report.total is None for report in compressing)

    def test_a_slice_reports_the_program_its_reconstruction_would(
        self,
        backend: NSFBackend,
        tmp_path: Path,
    ) -> None:
        alone: RecordingReporter[ExportProgress] = RecordingReporter()
        backend.write_instrument(tmp_path / FILENAME, lead_slice("lead", SOUNDING_TICKS), alone)
        assert reported_stages(alone.reports)[0] == ExportStage.WALKING


class TestWithdrawingARun:
    """A caller that stops wanting the program is left with no file to open."""

    def test_a_withdrawn_run_writes_nothing(self, backend: NSFBackend, tmp_path: Path) -> None:
        destination = tmp_path / FILENAME
        reporter: RecordingReporter[ExportProgress] = RecordingReporter(withdraw_at=WITHDRAWN_WHILE_WALKING)
        request = player_sample(SAMPLE_NAME, (lead_slice("lead", SOUNDING_TICKS),), nes_frequency=NTSC_FREQUENCY)
        with pytest.raises(OperationCancelled):
            backend.write_sample(destination, request, reporter)

        assert not destination.exists()

    def test_a_run_withdrawn_mid_compression_writes_nothing(
        self,
        backend: NSFBackend,
        tmp_path: Path,
    ) -> None:
        destination = tmp_path / FILENAME
        reporter: RecordingReporter[ExportProgress] = RecordingReporter(withdraw_at=WITHDRAWN_WHILE_COMPRESSING)
        request = player_sample(SAMPLE_NAME, (lead_slice("lead", SOUNDING_TICKS),), nes_frequency=NTSC_FREQUENCY)
        with pytest.raises(OperationCancelled):
            backend.write_sample(destination, request, reporter)

        assert reporter.last.stage == ExportStage.COMPRESSING
        assert not destination.exists()
