from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, Final, List
from unittest.mock import MagicMock

import pytest

from sampletones_application.exports import build_export_backends
from sampletones_application.logic.export.instrument import (
    InstrumentExportLogic,
    voice_instrument,
    voice_instruments,
)
from sampletones_core.constants.enums import ChannelName
from sampletones_core.exports.format import ExportFormat
from sampletones_core.exports.request import InstrumentSource
from sampletones_core.project.project import Project
from sampletones_core.project.voices.creation import new_instrument
from sampletones_core.project.voices.sample import Sample
from sampletones_core.reconstructions import Reconstruction
from sampletones_shared.music import Tuning
from sampletones_shared.paths.extensions import (
    EXT_FILE_BITPHASE,
    EXT_FILE_INSTRUMENT,
    EXT_FILE_JSON,
    EXT_FILE_MODULE,
    EXT_FILE_NSF,
)
from tests.suite.sequencer import sample_reconstruction

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
def logic(
    session_manager: MagicMock,
    export_service: MagicMock,
    export_backends: Dict[ExportFormat, MagicMock],
) -> InstrumentExportLogic:
    return InstrumentExportLogic(session_manager, export_service, export_backends)


def _source() -> InstrumentSource:
    voice = new_instrument("Lead")
    project = Project.create()
    project.voices.append(voice)
    return voice_instrument(project, voice_instruments(voice)[0]).source


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


class TestWhatAVoiceOffers:
    """One rule answers what a voice contributes, so both kinds are exported the same way."""

    @staticmethod
    def _project(*voices: object) -> Project:
        project = Project.create()
        for voice in voices:
            project.voices.append(voice)

        return project

    def test_a_written_instrument_offers_one(self) -> None:
        """One set of envelopes every channel reads is one instrument, as a module holds it."""
        voice = new_instrument("Lead")

        assert len(voice_instruments(voice)) == 1

    def test_a_written_instrument_is_named_after_itself(self) -> None:
        voice = new_instrument("Lead")

        assert voice_instruments(voice)[0].name == "Lead"

    def test_a_written_instrument_is_sounded_through_the_first_channel_it_reaches(self) -> None:
        """A file holding the instrument alone needs one channel to sound it on."""
        voice = new_instrument("Lead")

        assert voice_instruments(voice)[0].export_channel is ChannelName.PULSE1

    def test_a_sample_offers_one_per_channel_that_plays(
        self,
        reconstruction_factory: Callable[[], Reconstruction],
    ) -> None:
        sample = Sample(name="Bass", reconstruction=reconstruction_factory())
        playing = sample.reconstruction.playing_channels

        assert [entry.export_channel for entry in voice_instruments(sample)] == list(playing)

    def test_a_samples_slice_is_named_for_its_channel(
        self,
        reconstruction_factory: Callable[[], Reconstruction],
    ) -> None:
        sample = Sample(name="Bass", reconstruction=reconstruction_factory())

        assert all(entry.name.startswith("Bass") for entry in voice_instruments(sample))

    def test_both_kinds_answer_with_the_same_shape(
        self,
        reconstruction_factory: Callable[[], Reconstruction],
    ) -> None:
        """Whatever produced the envelopes is settled here, so one export path takes both."""
        sample = Sample(name="Bass", reconstruction=reconstruction_factory())
        written = new_instrument("Lead")
        project = self._project(sample, written)

        sources = [voice_instrument(project, entry).source for entry in voice_instruments(sample)]
        sources += [voice_instrument(project, entry).source for entry in voice_instruments(written)]

        assert all(isinstance(source, InstrumentSource) for source in sources)

    def test_the_project_states_the_rate_and_the_tuning(self) -> None:
        voice = new_instrument("Lead")
        project = self._project(voice)

        source = voice_instrument(project, voice_instruments(voice)[0]).source

        assert source.nes_frequency == project.settings.nes_frequency
        assert source.tuning == Tuning()

    def test_a_voice_with_nothing_written_offers_nothing(self) -> None:
        sample = Sample(name="Silent", reconstruction=sample_reconstruction(set()))

        assert voice_instruments(sample) == ()
