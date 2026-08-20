from pathlib import Path
from typing import Final

import pytest

from sampletones_core.constants.enums import ChannelName
from sampletones_core.exports.backend import ExportBackend
from sampletones_core.exports.format import ExportFormat
from sampletones_core.exports.request import InstrumentExport, ProjectExport
from sampletones_core.exports.scope import ExportScope
from sampletones_core.project.project import Project
from sampletones_core.project.settings import ProjectSettings
from sampletones_player.export import NSFBackend
from sampletones_player.specification.nsf import (
    ARTIST_OFFSET,
    HEADER_SIZE,
    PROGRAM_SIZE,
    STRING_FIELD_SIZE,
    TITLE_OFFSET,
)
from sampletones_shared.exceptions import SongTooLargeError
from sampletones_shared.paths.extensions import EXT_FILE_NSF
from tests.suite.player import (
    PLAYER_REFERENCE_PITCH,
    player_features,
    player_instrument,
    player_sample,
)

NTSC_FREQUENCY: Final[int] = 60
SOUNDING_TICKS: Final[int] = 8
BASS_PITCH: Final[int] = 45
OVERLONG_TICKS: Final[int] = PROGRAM_SIZE
FILENAME: Final[str] = "reconstruction.nsf"
SAMPLE_NAME: Final[str] = "Amen"
PROJECT_TITLE: Final[str] = "Demo"


def lead_slice(name: str, frames: int) -> InstrumentExport:
    return player_instrument(
        name,
        ChannelName.PULSE1,
        player_features(frames, PLAYER_REFERENCE_PITCH, duty_cycle=True),
        nes_frequency=NTSC_FREQUENCY,
        loop=False,
    )


def bass_slice(name: str, frames: int) -> InstrumentExport:
    return player_instrument(
        name,
        ChannelName.TRIANGLE,
        player_features(frames, BASS_PITCH, duty_cycle=False),
        nes_frequency=NTSC_FREQUENCY,
        loop=False,
    )


def read_field(data: bytes, offset: int) -> str:
    return data[offset : offset + STRING_FIELD_SIZE].rstrip(b"\x00").decode()


@pytest.fixture(name="backend")
def backend_fixture() -> NSFBackend:
    return NSFBackend()


class TestSeam:
    """What the backend answers the export seam with."""

    def test_the_backend_writes_the_nsf_format(self, backend: NSFBackend) -> None:
        assert backend.export_format == ExportFormat.NSF

    def test_a_program_plays_an_instrument_and_a_reconstruction(self, backend: NSFBackend) -> None:
        assert backend.supported_scopes == frozenset({ExportScope.INSTRUMENT, ExportScope.SAMPLE})

    @pytest.mark.parametrize("scope", [ExportScope.INSTRUMENT, ExportScope.SAMPLE])
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
        request = player_sample(SAMPLE_NAME, (lead_slice("lead", OVERLONG_TICKS),), nes_frequency=NTSC_FREQUENCY)
        with pytest.raises(SongTooLargeError):
            backend.write_sample(destination, request)


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


class TestWriteProject:
    """What a whole composition meets at the console's door."""

    def test_a_project_reaches_the_console_later(self, backend: NSFBackend, tmp_path: Path) -> None:
        project = Project.create(title=PROJECT_TITLE, settings=ProjectSettings())
        with pytest.raises(NotImplementedError):
            backend.write_project(tmp_path / FILENAME, ProjectExport(project=project))
