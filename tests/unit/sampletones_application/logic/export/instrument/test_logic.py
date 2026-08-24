from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, Final, List
from unittest.mock import MagicMock

import pytest

from sampletones_application.exports import build_export_backends
from sampletones_application.logic.export.instrument.logic import InstrumentExportLogic
from sampletones_application.logic.export.instrument.source import (
    exportable_instrument,
    voice_entries,
)
from sampletones_core.exports.format import ExportFormat
from sampletones_core.exports.request import InstrumentSource
from sampletones_core.project.project import Project
from sampletones_core.project.voices.creation import new_instrument
from sampletones_core.project.voices.sample import Sample
from sampletones_core.reconstructions import Reconstruction
from sampletones_shared.paths.extensions import (
    EXT_FILE_BITPHASE,
    EXT_FILE_INSTRUMENT,
    EXT_FILE_JSON,
    EXT_FILE_MODULE,
    EXT_FILE_NSF,
)

NO_EXTENSION: Final[str] = ""
REMEMBERED_DIRECTORY: Final[Path] = Path("/instruments")


@dataclass(frozen=True)
class FormatCase:
    extension: str
    export_format: ExportFormat


FORMAT_CASES: Final[List[FormatCase]] = [
    FormatCase(extension=EXT_FILE_INSTRUMENT, export_format=ExportFormat.FAMITRACKER),
    FormatCase(extension=EXT_FILE_BITPHASE, export_format=ExportFormat.BITPHASE),
    FormatCase(extension=EXT_FILE_JSON, export_format=ExportFormat.BITPHASE_PRESET),
    FormatCase(extension=EXT_FILE_NSF, export_format=ExportFormat.NSF),
]

UNSUPPORTED_EXTENSIONS: Final[List[str]] = [".xm", EXT_FILE_MODULE, NO_EXTENSION]


@pytest.fixture
def session_manager() -> MagicMock:
    mock = MagicMock()
    mock.get_instrument_path.return_value = REMEMBERED_DIRECTORY
    return mock


@pytest.fixture
def export_service() -> MagicMock:
    return MagicMock()


@pytest.fixture
def export_backends() -> Dict[ExportFormat, MagicMock]:
    """Stands in for the real backends while declaring the scopes and extensions they do."""
    backends: Dict[ExportFormat, MagicMock] = {}
    for export_format, backend in build_export_backends().items():
        stub = MagicMock()
        stub.supported_scopes = backend.supported_scopes
        stub.extension.side_effect = backend.extension
        backends[export_format] = stub

    return backends


@pytest.fixture
def project_controller() -> MagicMock:
    mock = MagicMock()
    mock.project = Project.create()
    return mock


@pytest.fixture
def logic(
    project_controller: MagicMock,
    session_manager: MagicMock,
    export_service: MagicMock,
    export_backends: Dict[ExportFormat, MagicMock],
) -> InstrumentExportLogic:
    return InstrumentExportLogic(project_controller, session_manager, export_service, export_backends)


def _source() -> InstrumentSource:
    voice = new_instrument("Lead")
    project = Project.create()
    project.voices.append(voice)
    return exportable_instrument(project, voice_entries(voice)[0]).source


class TestWritingOneInstrument:
    """One path carries an instrument to disk, whichever surface asked for it."""

    def test_the_service_is_asked_to_write_it(
        self,
        logic: InstrumentExportLogic,
        export_service: MagicMock,
        tmp_path: Path,
    ) -> None:
        logic.export(tmp_path / f"instrument{EXT_FILE_INSTRUMENT}", _source())

        export_service.export_instrument.assert_called_once()

    def test_the_destination_names_the_instrument(
        self,
        logic: InstrumentExportLogic,
        export_service: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Renaming the file in the save dialog renames the instrument the file carries."""
        logic.export(tmp_path / f"Clap (pulse1){EXT_FILE_INSTRUMENT}", _source())

        request = export_service.export_instrument.call_args.args[2]
        assert request.name == "Clap (pulse1)"

    @pytest.mark.parametrize("case", FORMAT_CASES, ids=lambda case: case.extension)
    def test_the_extension_names_the_backend(
        self,
        logic: InstrumentExportLogic,
        export_service: MagicMock,
        export_backends: Dict[ExportFormat, MagicMock],
        tmp_path: Path,
        case: FormatCase,
    ) -> None:
        logic.export(tmp_path / f"instrument{case.extension}", _source())

        backend = export_service.export_instrument.call_args.args[1]
        assert backend is export_backends[case.export_format]

    def test_everything_the_source_states_reaches_the_request(
        self,
        logic: InstrumentExportLogic,
        export_service: MagicMock,
        tmp_path: Path,
    ) -> None:
        source = _source()

        logic.export(tmp_path / f"instrument{EXT_FILE_INSTRUMENT}", source)

        request = export_service.export_instrument.call_args.args[2]
        assert (request.channel, request.features, request.loop_point) == (
            source.channel,
            source.features,
            source.loop_point,
        )
        assert (request.nes_frequency, request.tuning) == (source.nes_frequency, source.tuning)

    def test_the_folder_it_landed_in_is_remembered(
        self,
        logic: InstrumentExportLogic,
        session_manager: MagicMock,
        tmp_path: Path,
    ) -> None:
        logic.export(tmp_path / f"instrument{EXT_FILE_INSTRUMENT}", _source())

        session_manager.set_instrument_path.assert_called_once_with(tmp_path)

    def test_the_dialog_opens_where_the_last_one_landed(self, logic: InstrumentExportLogic) -> None:
        assert logic.suggested_directory == REMEMBERED_DIRECTORY

    def test_every_backend_is_reachable_for_the_types_a_dialog_offers(
        self,
        logic: InstrumentExportLogic,
        export_backends: Dict[ExportFormat, MagicMock],
    ) -> None:
        """The dialog names each format's own file type, which it reads off the backend."""
        assert dict(logic.backends) == export_backends

    @pytest.mark.parametrize("extension", UNSUPPORTED_EXTENSIONS)
    def test_an_extension_no_format_writes_is_refused(
        self,
        logic: InstrumentExportLogic,
        tmp_path: Path,
        extension: str,
    ) -> None:
        """The dialog answers with one of the types it offered, so an extension naming no
        format is a broken invariant rather than a choice to report.
        """
        with pytest.raises(ValueError):
            logic.export(tmp_path / f"instrument{extension}", _source())


class TestWhatTheOpenProjectOffers:
    """A menu names a voice alone, so the pool it belongs to is the one the logic holds."""

    def test_a_sample_of_the_open_project_offers_each_channel_that_plays(
        self,
        logic: InstrumentExportLogic,
        project_controller: MagicMock,
        reconstruction_factory: Callable[[], Reconstruction],
    ) -> None:
        sample = Sample(name="Bass", reconstruction=reconstruction_factory())
        project_controller.project.voices.append(sample)

        assert logic.voice_instruments(sample.id) == tuple(sample.reconstruction.playing_channels)

    def test_the_instrument_asked_for_comes_from_the_open_project(
        self,
        logic: InstrumentExportLogic,
        project_controller: MagicMock,
    ) -> None:
        voice = new_instrument("Lead")
        project_controller.project.voices.append(voice)

        exportable = logic.voice_instrument(voice.id, None)

        assert exportable is not None
        assert exportable.name == "Lead"
