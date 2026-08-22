from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, Final, List
from unittest.mock import MagicMock

import numpy as np
import pytest

from sampletones_application.exports import build_export_backends
from sampletones_application.logic.reconstruction.data import ReconstructionData
from sampletones_application.logic.reconstruction.manager import ReconstructionManager
from sampletones_application.logic.reconstruction.reconstruction import (
    ReconstructionPanelLogic,
)
from sampletones_application.view_model.reconstruction.paths.state import (
    ReconstructionPathState,
)
from sampletones_application.view_model.reconstruction.reconstruction import (
    ReconstructionViewModel,
)
from sampletones_core.audio import write_wave
from sampletones_core.configs import Config
from sampletones_core.constants.enums import AudioSourceType, ChannelName
from sampletones_core.exports.format import ExportFormat
from sampletones_core.instructions import TriangleInstruction
from sampletones_core.reconstructions import Reconstruction
from sampletones_core.reconstructions.reconstruction.stems.channel_assignment import ChannelAssignment
from sampletones_core.reconstructions.reconstruction.stems.data import StemsData
from sampletones_core.reconstructions.reconstructor.stems.configs.config import StemsConfig
from sampletones_core.reconstructions.reconstructor.stems.configs.entry import StemEntry
from sampletones_core.reconstructions.reconstructor.stems.configs.hierarchy import StemsHierarchy
from sampletones_shared.music import Tuning
from sampletones_shared.paths.extensions import (
    EXT_FILE_BITPHASE,
    EXT_FILE_INSTRUMENT,
    EXT_FILE_JSON,
    EXT_FILE_MODULE,
    EXT_FILE_NSF,
)
from tests.suite.case import BaseRegularTestCase

NO_EXTENSION: Final[str] = ""
RETUNED_A4_FREQUENCY: Final[float] = 432.0


@dataclass(frozen=True)
class FormatCase:
    extension: str
    export_format: ExportFormat


INSTRUMENT_FORMAT_CASES: Final[List[FormatCase]] = [
    FormatCase(extension=EXT_FILE_INSTRUMENT, export_format=ExportFormat.FAMITRACKER),
    FormatCase(extension=EXT_FILE_BITPHASE, export_format=ExportFormat.BITPHASE),
    FormatCase(extension=EXT_FILE_JSON, export_format=ExportFormat.BITPHASE_PRESET),
    FormatCase(extension=EXT_FILE_NSF, export_format=ExportFormat.NSF),
]

UNSUPPORTED_EXTENSIONS: Final[List[str]] = [".xm", EXT_FILE_MODULE, NO_EXTENSION]


@pytest.fixture
def session_manager() -> MagicMock:
    mock = MagicMock()
    mock.get_instrument_path.return_value = Path("/tmp/instruments")
    mock.get_audio_path.return_value = Path("/tmp/audio")
    return mock


@pytest.fixture
def mock_export_service() -> MagicMock:
    return MagicMock()


@pytest.fixture
def mock_reconstruction_manager() -> MagicMock:
    mock = MagicMock(spec=ReconstructionManager)
    mock.current_reconstruction = None
    mock.audio_filepath = None
    return mock


@pytest.fixture
def panel_logic(
    session_manager: MagicMock,
    mock_reconstruction_manager: MagicMock,
    mock_export_service: MagicMock,
    mock_export_backends: Dict[ExportFormat, MagicMock],
) -> ReconstructionPanelLogic:
    return ReconstructionPanelLogic(
        session_manager,
        mock_reconstruction_manager,
        mock_export_service,
        mock_export_backends,
    )


@pytest.fixture
def mock_export_backends() -> Dict[ExportFormat, MagicMock]:
    """Stands in for the real backends while declaring the scopes and extensions they do.

    The logic reads the destination's extension to pick a backend, so each stub mirrors what
    the registry's backend declares and leaves only the writing to the mock.
    """
    backends: Dict[ExportFormat, MagicMock] = {}
    for export_format, backend in build_export_backends().items():
        stub = MagicMock()
        stub.supported_scopes = backend.supported_scopes
        stub.extension.side_effect = backend.extension
        backends[export_format] = stub

    return backends


@pytest.fixture
def loaded_data(
    reconstruction_factory: Callable[[], Reconstruction],
) -> ReconstructionData:
    return ReconstructionData.from_reconstruction(
        reconstruction_factory(),
        name="Sample",
    )


@pytest.fixture
def retuned_data(
    reconstruction_factory: Callable[[], Reconstruction],
) -> ReconstructionData:
    """A reconstruction built against a concert pitch other than the standard one."""
    reconstruction = reconstruction_factory()
    library = reconstruction.config.library.model_copy(update={"a4_frequency": RETUNED_A4_FREQUENCY})
    config = reconstruction.config.model_copy(update={"library": library})
    return ReconstructionData.from_reconstruction(
        reconstruction.model_copy(update={"config": config}),
        name="Sample",
    )


@pytest.fixture
def data_with_original_audio(
    reconstruction_factory: Callable[[], Reconstruction],
    tmp_path: Path,
) -> ReconstructionData:
    source_audio = tmp_path / "source.wav"
    write_wave(
        source_audio,
        Config().library.sample_rate,
        np.ones(64, dtype=np.float32) * 0.5,
    )
    reconstruction = reconstruction_factory().model_copy(update={"audio_filepath": (source_audio,)})
    return ReconstructionData.from_reconstruction(reconstruction, name="Sample")


class TestReconstructionPanelLogicDisplay:
    def test_display_with_no_data_is_no_op(
        self,
        panel_logic: ReconstructionPanelLogic,
    ) -> None:
        callback = MagicMock()
        panel_logic.on_view_changed = callback
        panel_logic.display_reconstruction()
        callback.assert_not_called()

    def test_display_fires_on_view_changed(
        self,
        panel_logic: ReconstructionPanelLogic,
        mock_reconstruction_manager: MagicMock,
        loaded_data: ReconstructionData,
    ) -> None:
        mock_reconstruction_manager.current_reconstruction = loaded_data
        callback = MagicMock()
        panel_logic.on_view_changed = callback
        panel_logic.display_reconstruction()
        callback.assert_called_once()

    def test_display_fires_on_waveform_load_changed(
        self,
        panel_logic: ReconstructionPanelLogic,
        mock_reconstruction_manager: MagicMock,
        loaded_data: ReconstructionData,
    ) -> None:
        mock_reconstruction_manager.current_reconstruction = loaded_data
        callback = MagicMock()
        panel_logic.on_waveform_load_changed = callback
        panel_logic.display_reconstruction()
        callback.assert_called_once()

    def test_display_fires_on_audio_data_changed(
        self,
        panel_logic: ReconstructionPanelLogic,
        mock_reconstruction_manager: MagicMock,
        loaded_data: ReconstructionData,
    ) -> None:
        mock_reconstruction_manager.current_reconstruction = loaded_data
        callback = MagicMock()
        panel_logic.on_audio_data_changed = callback
        panel_logic.display_reconstruction()
        callback.assert_called_once()


class TestReconstructionPanelLogicPathRows:
    def test_detached_reconstruction_reports_both_locations_not_applicable(
        self,
        panel_logic: ReconstructionPanelLogic,
        mock_reconstruction_manager: MagicMock,
        reconstruction_factory: Callable[[], Reconstruction],
    ) -> None:
        reconstruction = reconstruction_factory()
        reconstruction.detach_source()
        mock_reconstruction_manager.current_reconstruction = ReconstructionData.from_reconstruction(
            reconstruction,
            name="Sample",
        )
        captured: List[ReconstructionViewModel] = []
        panel_logic.on_view_changed = captured.append

        panel_logic.display_reconstruction()

        view_model = captured[0]
        assert view_model.reconstruction_file.state is ReconstructionPathState.NOT_APPLICABLE
        assert view_model.original_audio.state is ReconstructionPathState.NOT_APPLICABLE

    @dataclass(frozen=True, kw_only=True)
    class AudioPathCase(BaseRegularTestCase):
        has_filepath: bool
        has_content: bool
        expected: ReconstructionPathState

    test_cases = (
        AudioPathCase(
            label="detached",
            has_filepath=False,
            has_content=False,
            expected=ReconstructionPathState.NOT_APPLICABLE,
        ),
        AudioPathCase(
            label="recorded_but_unavailable",
            has_filepath=True,
            has_content=False,
            expected=ReconstructionPathState.NOT_FOUND,
        ),
        AudioPathCase(
            label="available",
            has_filepath=True,
            has_content=True,
            expected=ReconstructionPathState.AVAILABLE,
        ),
    )

    @pytest.mark.parametrize("case", test_cases, ids=lambda case: case.label)
    def test_audio_path_state_follows_loaded_content(self, case: AudioPathCase) -> None:
        source_paths = (Path("/songs/source.wav"),) if case.has_filepath else ()
        original_audio = np.zeros(4, dtype=np.float32) if case.has_content else None

        view_model = ReconstructionPanelLogic._build_audio_path_view_model(
            source_paths,
            original_audio,
        )

        assert view_model.state is case.expected

    def test_stem_paths_report_multiple_state(self) -> None:
        stem_paths = (
            Path("/stems/drums/kick.wav"),
            Path("/stems/drums/snare.wav"),
        )
        original_audio = np.zeros(4, dtype=np.float32)

        view_model = ReconstructionPanelLogic._build_audio_path_view_model(
            stem_paths,
            original_audio,
        )

        assert view_model.state is ReconstructionPathState.MULTIPLE
        assert view_model.paths == tuple(str(path) for path in stem_paths)
        assert view_model.path == ""


class TestReconstructionPanelLogicUpdate:
    def test_update_with_no_data_is_no_op(
        self,
        panel_logic: ReconstructionPanelLogic,
    ) -> None:
        callback = MagicMock()
        panel_logic.on_waveform_update_changed = callback
        panel_logic.update_reconstruction()
        callback.assert_not_called()

    def test_update_fires_on_waveform_update_changed(
        self,
        panel_logic: ReconstructionPanelLogic,
        mock_reconstruction_manager: MagicMock,
        loaded_data: ReconstructionData,
    ) -> None:
        mock_reconstruction_manager.current_reconstruction = loaded_data
        callback = MagicMock()
        panel_logic.on_waveform_update_changed = callback
        panel_logic.update_reconstruction()
        callback.assert_called_once()

    def test_update_emits_audio_when_source_is_not_original(
        self,
        panel_logic: ReconstructionPanelLogic,
        mock_reconstruction_manager: MagicMock,
        loaded_data: ReconstructionData,
    ) -> None:
        mock_reconstruction_manager.current_reconstruction = loaded_data
        callback = MagicMock()
        panel_logic.on_audio_data_changed = callback
        panel_logic.update_reconstruction()
        callback.assert_called_once()

    def test_update_skips_audio_when_source_is_original(
        self,
        panel_logic: ReconstructionPanelLogic,
        mock_reconstruction_manager: MagicMock,
        loaded_data: ReconstructionData,
    ) -> None:
        mock_reconstruction_manager.current_reconstruction = loaded_data
        panel_logic._current_audio_source = AudioSourceType.ORIGINAL
        callback = MagicMock()
        panel_logic.on_audio_data_changed = callback
        panel_logic.update_reconstruction()
        callback.assert_not_called()


class TestReconstructionPanelLogicPlayingChannels:
    """Which channels the waveform offers, and what an edit does to the reader's choice."""

    @staticmethod
    def _received(panel_logic: ReconstructionPanelLogic) -> List[ReconstructionViewModel]:
        received: List[ReconstructionViewModel] = []
        panel_logic.on_view_changed = received.append
        return received

    def test_display_offers_the_channels_that_play(
        self,
        panel_logic: ReconstructionPanelLogic,
        mock_reconstruction_manager: MagicMock,
        loaded_data: ReconstructionData,
    ) -> None:
        mock_reconstruction_manager.current_reconstruction = loaded_data
        received = self._received(panel_logic)

        panel_logic.display_reconstruction()

        assert received[0].playing_channels == frozenset({ChannelName.PULSE1})
        assert received[0].selected_channels == frozenset({ChannelName.PULSE1})

    def test_an_edit_reports_the_view_again(
        self,
        panel_logic: ReconstructionPanelLogic,
        mock_reconstruction_manager: MagicMock,
        loaded_data: ReconstructionData,
    ) -> None:
        mock_reconstruction_manager.current_reconstruction = loaded_data
        panel_logic.display_reconstruction()
        received = self._received(panel_logic)

        panel_logic.update_reconstruction()

        assert received[0].playing_channels == frozenset({ChannelName.PULSE1})

    def test_a_channel_switched_off_by_hand_survives_an_edit(
        self,
        panel_logic: ReconstructionPanelLogic,
        mock_reconstruction_manager: MagicMock,
        loaded_data: ReconstructionData,
    ) -> None:
        mock_reconstruction_manager.current_reconstruction = loaded_data
        panel_logic.display_reconstruction()
        panel_logic.set_selected_channels([])
        received = self._received(panel_logic)

        panel_logic.update_reconstruction()

        assert received[0].selected_channels == frozenset()

    def test_a_channel_gaining_its_first_frame_joins_the_waveform(
        self,
        panel_logic: ReconstructionPanelLogic,
        mock_reconstruction_manager: MagicMock,
        loaded_data: ReconstructionData,
    ) -> None:
        mock_reconstruction_manager.current_reconstruction = loaded_data
        panel_logic.display_reconstruction()
        loaded_data.reconstruction.update_channel_data(
            ChannelName.TRIANGLE,
            [TriangleInstruction(on=True, pitch=48)],
            np.ones(64, dtype=np.float32),
            48,
            (),
        )
        received = self._received(panel_logic)

        panel_logic.update_reconstruction()

        assert received[0].playing_channels == frozenset({ChannelName.PULSE1, ChannelName.TRIANGLE})
        assert received[0].selected_channels == frozenset({ChannelName.PULSE1, ChannelName.TRIANGLE})

    def test_a_channel_taken_out_of_play_leaves_the_waveform(
        self,
        panel_logic: ReconstructionPanelLogic,
        mock_reconstruction_manager: MagicMock,
        loaded_data: ReconstructionData,
    ) -> None:
        mock_reconstruction_manager.current_reconstruction = loaded_data
        panel_logic.display_reconstruction()
        loaded_data.reconstruction.update_channel_data(
            ChannelName.PULSE1,
            [],
            np.zeros(0, dtype=np.float32),
            60,
            (),
        )
        received = self._received(panel_logic)

        panel_logic.update_reconstruction()

        assert received[0].playing_channels == frozenset()
        assert received[0].selected_channels == frozenset()


class TestReconstructionPanelLogicClose:
    def test_close_fires_on_waveform_cleared(
        self,
        panel_logic: ReconstructionPanelLogic,
    ) -> None:
        callback = MagicMock()
        panel_logic.on_waveform_cleared = callback
        panel_logic.close_reconstruction()
        callback.assert_called_once()

    def test_close_fires_on_view_changed_with_not_loaded(
        self,
        panel_logic: ReconstructionPanelLogic,
    ) -> None:
        received = []
        panel_logic.on_view_changed = lambda vm: received.append(vm)
        panel_logic.close_reconstruction()
        assert len(received) == 1
        assert received[0].reconstruction_loaded is False

    def test_close_fires_on_audio_data_changed_with_none(
        self,
        panel_logic: ReconstructionPanelLogic,
    ) -> None:
        received = []
        panel_logic.on_audio_data_changed = received.append
        panel_logic.close_reconstruction()
        assert received == [None]

    def test_close_resets_audio_source_to_reconstruction(
        self,
        panel_logic: ReconstructionPanelLogic,
        mock_reconstruction_manager: MagicMock,
        loaded_data: ReconstructionData,
    ) -> None:
        mock_reconstruction_manager.current_reconstruction = loaded_data
        panel_logic.set_audio_source(AudioSourceType.ORIGINAL)
        panel_logic.close_reconstruction()
        assert panel_logic._current_audio_source == AudioSourceType.RECONSTRUCTION


class TestReconstructionPanelLogicAudioSource:
    def test_display_without_original_audio_switches_source_to_reconstruction(
        self,
        panel_logic: ReconstructionPanelLogic,
        mock_reconstruction_manager: MagicMock,
        reconstruction_factory: Callable[[], Reconstruction],
    ) -> None:
        reconstruction = reconstruction_factory()
        reconstruction.detach_source()
        mock_reconstruction_manager.current_reconstruction = ReconstructionData.from_reconstruction(
            reconstruction, name="Sample"
        )
        panel_logic.set_audio_source(AudioSourceType.ORIGINAL)
        received: List[AudioSourceType] = []
        panel_logic.on_waveform_source_changed = received.append

        panel_logic.display_reconstruction()

        assert received == [AudioSourceType.RECONSTRUCTION]

    def test_display_with_original_audio_keeps_selected_source(
        self,
        panel_logic: ReconstructionPanelLogic,
        mock_reconstruction_manager: MagicMock,
        data_with_original_audio: ReconstructionData,
    ) -> None:
        mock_reconstruction_manager.current_reconstruction = data_with_original_audio
        panel_logic.set_audio_source(AudioSourceType.ORIGINAL)
        received: List[AudioSourceType] = []
        panel_logic.on_waveform_source_changed = received.append

        panel_logic.display_reconstruction()

        assert received == [AudioSourceType.ORIGINAL]

    def test_set_audio_source_changes_to_original(
        self,
        panel_logic: ReconstructionPanelLogic,
        mock_reconstruction_manager: MagicMock,
        loaded_data: ReconstructionData,
    ) -> None:
        mock_reconstruction_manager.current_reconstruction = loaded_data
        panel_logic.set_audio_source(AudioSourceType.ORIGINAL)
        assert panel_logic._current_audio_source == AudioSourceType.ORIGINAL

    def test_set_audio_source_emits_audio_data(
        self,
        panel_logic: ReconstructionPanelLogic,
        mock_reconstruction_manager: MagicMock,
        loaded_data: ReconstructionData,
    ) -> None:
        mock_reconstruction_manager.current_reconstruction = loaded_data
        callback = MagicMock()
        panel_logic.on_audio_data_changed = callback
        panel_logic.set_audio_source(AudioSourceType.ORIGINAL)
        callback.assert_called_once()


class TestReconstructionPanelLogicSelectedChannels:
    def test_set_selected_generators_updates_selection(
        self,
        panel_logic: ReconstructionPanelLogic,
        mock_reconstruction_manager: MagicMock,
        loaded_data: ReconstructionData,
    ) -> None:
        mock_reconstruction_manager.current_reconstruction = loaded_data
        panel_logic.set_selected_channels([ChannelName.PULSE1])
        assert panel_logic._selected_channels == [ChannelName.PULSE1]

    def test_set_selected_generators_fires_waveform_load(
        self,
        panel_logic: ReconstructionPanelLogic,
        mock_reconstruction_manager: MagicMock,
        loaded_data: ReconstructionData,
    ) -> None:
        mock_reconstruction_manager.current_reconstruction = loaded_data
        callback = MagicMock()
        panel_logic.on_waveform_load_changed = callback
        panel_logic.set_selected_channels([ChannelName.PULSE1])
        callback.assert_called_once()

    def test_set_selected_generators_with_no_data_skips_waveform(
        self,
        panel_logic: ReconstructionPanelLogic,
    ) -> None:
        callback = MagicMock()
        panel_logic.on_waveform_load_changed = callback
        panel_logic.set_selected_channels([ChannelName.PULSE1])
        callback.assert_not_called()


class TestReconstructionPanelLogicExportInstrument:
    def test_request_export_instrument_dialog_with_no_data_raises_assertion_error(
        self,
        panel_logic: ReconstructionPanelLogic,
    ) -> None:
        with pytest.raises(AssertionError):
            panel_logic.request_export_instrument_dialog(ChannelName.PULSE1)

    def test_request_export_instrument_dialog_fires_dialog_callback(
        self,
        panel_logic: ReconstructionPanelLogic,
        mock_reconstruction_manager: MagicMock,
        loaded_data: ReconstructionData,
    ) -> None:
        mock_reconstruction_manager.current_reconstruction = loaded_data
        callback = MagicMock()
        panel_logic.on_open_export_instrument_dialog = callback
        panel_logic.request_export_instrument_dialog(ChannelName.PULSE1)
        callback.assert_called_once()

    def test_request_export_instrument_dialog_suggests_the_slice_name(
        self,
        panel_logic: ReconstructionPanelLogic,
        mock_reconstruction_manager: MagicMock,
        loaded_data: ReconstructionData,
    ) -> None:
        """The suggestion is the slice name alone, leaving the tracker to the dialog's own
        file-type selector.
        """
        mock_reconstruction_manager.current_reconstruction = loaded_data
        callback = MagicMock()
        panel_logic.on_open_export_instrument_dialog = callback
        panel_logic.request_export_instrument_dialog(ChannelName.PULSE1)
        assert callback.call_args.args[0] == "Sample (pulse1)"

    def test_request_export_instrument_dialog_for_unknown_generator_is_no_op(
        self,
        panel_logic: ReconstructionPanelLogic,
        mock_reconstruction_manager: MagicMock,
        loaded_data: ReconstructionData,
    ) -> None:
        mock_reconstruction_manager.current_reconstruction = loaded_data
        callback = MagicMock()
        panel_logic.on_open_export_instrument_dialog = callback
        panel_logic.request_export_instrument_dialog(ChannelName.TRIANGLE)
        callback.assert_not_called()

    def test_request_export_instrument_dialog_sends_the_generator_to_the_dialog(
        self,
        panel_logic: ReconstructionPanelLogic,
        mock_reconstruction_manager: MagicMock,
        loaded_data: ReconstructionData,
    ) -> None:
        """The channel travels with the request, so the confirmation names it back."""
        mock_reconstruction_manager.current_reconstruction = loaded_data
        callback = MagicMock()
        panel_logic.on_open_export_instrument_dialog = callback
        panel_logic.request_export_instrument_dialog(ChannelName.PULSE1)
        assert callback.call_args.args[2] == ChannelName.PULSE1

    def test_handle_export_instrument_confirmed_with_no_data_does_not_export(
        self,
        panel_logic: ReconstructionPanelLogic,
        mock_export_service: MagicMock,
        tmp_path: Path,
    ) -> None:
        panel_logic.handle_export_instrument_confirmed(
            tmp_path / "instrument.fti",
            ChannelName.PULSE1,
        )
        mock_export_service.export_instrument.assert_not_called()

    def test_handle_export_instrument_confirmed_calls_export_service(
        self,
        panel_logic: ReconstructionPanelLogic,
        mock_reconstruction_manager: MagicMock,
        loaded_data: ReconstructionData,
        mock_export_service: MagicMock,
        tmp_path: Path,
    ) -> None:
        mock_reconstruction_manager.current_reconstruction = loaded_data
        panel_logic.handle_export_instrument_confirmed(
            tmp_path / "instrument.fti",
            ChannelName.PULSE1,
        )
        mock_export_service.export_instrument.assert_called_once()

    def test_handle_export_instrument_confirmed_names_the_instrument_after_the_destination(
        self,
        panel_logic: ReconstructionPanelLogic,
        mock_reconstruction_manager: MagicMock,
        loaded_data: ReconstructionData,
        mock_export_service: MagicMock,
        tmp_path: Path,
    ) -> None:
        mock_reconstruction_manager.current_reconstruction = loaded_data
        panel_logic.handle_export_instrument_confirmed(
            tmp_path / "Clap (pulse1).fti",
            ChannelName.PULSE1,
        )
        request = mock_export_service.export_instrument.call_args.args[2]
        assert request.name == "Clap (pulse1)"

    @pytest.mark.parametrize("case", INSTRUMENT_FORMAT_CASES, ids=lambda case: case.extension)
    def test_handle_export_instrument_confirmed_selects_the_backend_the_extension_names(
        self,
        panel_logic: ReconstructionPanelLogic,
        mock_reconstruction_manager: MagicMock,
        loaded_data: ReconstructionData,
        mock_export_service: MagicMock,
        mock_export_backends: Dict[ExportFormat, MagicMock],
        tmp_path: Path,
        case: FormatCase,
    ) -> None:
        mock_reconstruction_manager.current_reconstruction = loaded_data
        panel_logic.handle_export_instrument_confirmed(
            tmp_path / f"instrument{case.extension}",
            ChannelName.PULSE1,
        )
        backend = mock_export_service.export_instrument.call_args.args[1]
        assert backend is mock_export_backends[case.export_format]

    def test_handle_export_instrument_confirmed_carries_the_reconstructions_tuning(
        self,
        panel_logic: ReconstructionPanelLogic,
        mock_reconstruction_manager: MagicMock,
        retuned_data: ReconstructionData,
        mock_export_service: MagicMock,
        tmp_path: Path,
    ) -> None:
        """A backend sounding the export itself measures its pitches from the tuning the
        reconstruction was built with, so the request states that tuning rather than the standard.
        """
        mock_reconstruction_manager.current_reconstruction = retuned_data
        panel_logic.handle_export_instrument_confirmed(
            tmp_path / "instrument.fti",
            ChannelName.PULSE1,
        )
        request = mock_export_service.export_instrument.call_args.args[2]
        assert request.tuning == Tuning(a4_frequency=RETUNED_A4_FREQUENCY)

    @pytest.mark.parametrize("extension", UNSUPPORTED_EXTENSIONS)
    def test_handle_export_instrument_confirmed_refuses_an_extension_no_format_writes(
        self,
        panel_logic: ReconstructionPanelLogic,
        mock_reconstruction_manager: MagicMock,
        loaded_data: ReconstructionData,
        tmp_path: Path,
        extension: str,
    ) -> None:
        """The dialog answers with one of the types it offered, so an extension naming no
        format is a broken invariant rather than a choice to report.
        """
        mock_reconstruction_manager.current_reconstruction = loaded_data
        with pytest.raises(ValueError):
            panel_logic.handle_export_instrument_confirmed(
                tmp_path / f"instrument{extension}",
                ChannelName.PULSE1,
            )


class TestReconstructionPanelLogicExportInstruments:
    def test_request_export_instruments_dialog_with_no_data_raises_assertion_error(
        self,
        panel_logic: ReconstructionPanelLogic,
    ) -> None:
        with pytest.raises(AssertionError):
            panel_logic.request_export_instruments_dialog(ExportFormat.FAMITRACKER)

    def test_request_export_instruments_dialog_fires_dialog_callback(
        self,
        panel_logic: ReconstructionPanelLogic,
        mock_reconstruction_manager: MagicMock,
        loaded_data: ReconstructionData,
    ) -> None:
        mock_reconstruction_manager.current_reconstruction = loaded_data
        callback = MagicMock()
        panel_logic.on_open_export_instruments_dialog = callback
        panel_logic.request_export_instruments_dialog(ExportFormat.FAMITRACKER)
        callback.assert_called_once()

    def test_request_export_instruments_dialog_suggests_the_reconstruction_name(
        self,
        panel_logic: ReconstructionPanelLogic,
        mock_reconstruction_manager: MagicMock,
        loaded_data: ReconstructionData,
    ) -> None:
        """The tracker is settled before the dialog opens, so the suggestion ends in the
        extension that tracker writes.
        """
        mock_reconstruction_manager.current_reconstruction = loaded_data
        callback = MagicMock()
        panel_logic.on_open_export_instruments_dialog = callback
        panel_logic.request_export_instruments_dialog(ExportFormat.FAMITRACKER)
        assert callback.call_args.args[0] == f"{loaded_data.name}{EXT_FILE_INSTRUMENT}"

    def test_request_export_instruments_dialog_carries_the_chosen_tracker(
        self,
        panel_logic: ReconstructionPanelLogic,
        mock_reconstruction_manager: MagicMock,
        loaded_data: ReconstructionData,
    ) -> None:
        """The dialog offers one type, so the tracker travels with the request."""
        mock_reconstruction_manager.current_reconstruction = loaded_data
        callback = MagicMock()
        panel_logic.on_open_export_instruments_dialog = callback
        panel_logic.request_export_instruments_dialog(ExportFormat.BITPHASE_PRESET)
        assert callback.call_args.args[2] == ExportFormat.BITPHASE_PRESET

    def test_handle_export_instruments_confirmed_with_no_data_is_no_op(
        self,
        panel_logic: ReconstructionPanelLogic,
        mock_export_service: MagicMock,
        tmp_path: Path,
    ) -> None:
        panel_logic.handle_export_instruments_confirmed(
            tmp_path / "sample.fti",
            ExportFormat.FAMITRACKER,
        )
        mock_export_service.export_sample.assert_not_called()

    def test_handle_export_instruments_confirmed_calls_export_sample(
        self,
        panel_logic: ReconstructionPanelLogic,
        mock_reconstruction_manager: MagicMock,
        loaded_data: ReconstructionData,
        mock_export_service: MagicMock,
        tmp_path: Path,
    ) -> None:
        mock_reconstruction_manager.current_reconstruction = loaded_data
        panel_logic.handle_export_instruments_confirmed(
            tmp_path / "sample.fti",
            ExportFormat.FAMITRACKER,
        )
        mock_export_service.export_sample.assert_called_once()

    def test_handle_export_instruments_confirmed_names_the_batch_after_the_destination(
        self,
        panel_logic: ReconstructionPanelLogic,
        mock_reconstruction_manager: MagicMock,
        loaded_data: ReconstructionData,
        mock_export_service: MagicMock,
        tmp_path: Path,
    ) -> None:
        mock_reconstruction_manager.current_reconstruction = loaded_data
        panel_logic.handle_export_instruments_confirmed(
            tmp_path / "Clap.fti",
            ExportFormat.FAMITRACKER,
        )
        request = mock_export_service.export_sample.call_args.args[2]
        assert request.name == "Clap"
        assert [instrument.name for instrument in request.instruments] == ["Clap (pulse1)"]

    def test_handle_export_instruments_confirmed_carries_the_reconstructions_tuning(
        self,
        panel_logic: ReconstructionPanelLogic,
        mock_reconstruction_manager: MagicMock,
        retuned_data: ReconstructionData,
        mock_export_service: MagicMock,
        tmp_path: Path,
    ) -> None:
        mock_reconstruction_manager.current_reconstruction = retuned_data
        panel_logic.handle_export_instruments_confirmed(
            tmp_path / "Clap.fti",
            ExportFormat.FAMITRACKER,
        )
        request = mock_export_service.export_sample.call_args.args[2]
        retuned = Tuning(a4_frequency=RETUNED_A4_FREQUENCY)
        assert request.tuning == retuned
        assert [instrument.tuning for instrument in request.instruments] == [retuned]

    @pytest.mark.parametrize(
        "case",
        INSTRUMENT_FORMAT_CASES,
        ids=lambda case: case.extension,
    )
    def test_handle_export_instruments_confirmed_writes_through_the_chosen_tracker(
        self,
        panel_logic: ReconstructionPanelLogic,
        mock_reconstruction_manager: MagicMock,
        loaded_data: ReconstructionData,
        mock_export_service: MagicMock,
        mock_export_backends: Dict[ExportFormat, MagicMock],
        tmp_path: Path,
        case: FormatCase,
    ) -> None:
        """The action names the tracker, so the destination's own extension leaves the
        backend it is written through untouched.
        """
        mock_reconstruction_manager.current_reconstruction = loaded_data
        panel_logic.handle_export_instruments_confirmed(
            tmp_path / f"sample{case.extension}",
            case.export_format,
        )
        backend = mock_export_service.export_sample.call_args.args[1]
        assert backend is mock_export_backends[case.export_format]


class TestReconstructionPanelLogicExportWav:
    def test_request_export_wav_dialog_with_no_data_raises_assertion_error(
        self,
        panel_logic: ReconstructionPanelLogic,
    ) -> None:
        with pytest.raises(AssertionError):
            panel_logic.request_export_wav_dialog()

    def test_request_export_wav_dialog_fires_dialog_callback(
        self,
        panel_logic: ReconstructionPanelLogic,
        mock_reconstruction_manager: MagicMock,
        loaded_data: ReconstructionData,
    ) -> None:
        mock_reconstruction_manager.current_reconstruction = loaded_data
        callback = MagicMock()
        panel_logic.on_open_export_wav_dialog = callback
        panel_logic.request_export_wav_dialog()
        callback.assert_called_once()

    def test_handle_export_wav_confirmed_with_no_data_is_no_op(
        self,
        panel_logic: ReconstructionPanelLogic,
        mock_export_service: MagicMock,
        tmp_path: Path,
    ) -> None:
        panel_logic.handle_export_wav_confirmed(tmp_path / "output.wav")
        mock_export_service.export_wav.assert_not_called()

    def test_handle_export_wav_confirmed_calls_export_wav_with_sample_rate(
        self,
        panel_logic: ReconstructionPanelLogic,
        mock_reconstruction_manager: MagicMock,
        loaded_data: ReconstructionData,
        mock_export_service: MagicMock,
        tmp_path: Path,
    ) -> None:
        mock_reconstruction_manager.current_reconstruction = loaded_data
        panel_logic._selected_channels = [ChannelName.PULSE1]
        panel_logic.handle_export_wav_confirmed(tmp_path / "output.wav")
        mock_export_service.export_wav.assert_called_once()
        call_args = mock_export_service.export_wav.call_args
        assert call_args.args[1] == loaded_data.reconstruction.config.sample_rate


class TestReconstructionPanelLogicComputeAudio:
    def test_set_audio_source_with_no_data_emits_none(
        self,
        panel_logic: ReconstructionPanelLogic,
    ) -> None:
        received = []
        panel_logic.on_audio_data_changed = received.append
        panel_logic.set_audio_source(AudioSourceType.ORIGINAL)
        assert received == [None]


class TestReconstructionPanelLogicLocateAudio:
    def test_no_source_paths_skips_locating(
        self,
        panel_logic: ReconstructionPanelLogic,
        mock_reconstruction_manager: MagicMock,
    ) -> None:
        mock_reconstruction_manager.source_paths = ()
        panel_logic.handle_locate_original_audio()
        mock_reconstruction_manager.locate_original_audio.assert_not_called()

    def test_missing_audio_file_fires_on_locate_audio_not_found(
        self,
        panel_logic: ReconstructionPanelLogic,
        mock_reconstruction_manager: MagicMock,
        tmp_path: Path,
    ) -> None:
        missing = tmp_path / "ghost.wav"
        mock_reconstruction_manager.source_paths = (missing,)
        mock_reconstruction_manager.locate_original_audio.side_effect = FileNotFoundError
        callback = MagicMock()
        panel_logic.on_locate_audio_not_found = callback
        panel_logic.handle_locate_original_audio()
        callback.assert_called_once_with(missing)


class TestReconstructionPanelLogicStemSelection:
    @pytest.fixture(name="stems_data")
    def stems_data_fixture(
        self,
        reconstruction_factory: Callable[[], Reconstruction],
        tmp_path: Path,
    ) -> ReconstructionData:
        reconstruction = reconstruction_factory()
        frame_count = len(reconstruction.approximations[ChannelName.PULSE1]) // reconstruction.config.frame_length
        stems_config = StemsConfig(
            entries=[
                StemEntry(id=0, channels=[ChannelName.PULSE1]),
                StemEntry(id=1, channels=[ChannelName.PULSE1]),
            ],
            hierarchy=StemsHierarchy(levels=[[0, 1]]),
        )
        stems_reconstruction = reconstruction.model_copy(
            update={
                "audio_filepath": (tmp_path / "a.wav", tmp_path / "b.wav"),
                "stems_data": StemsData(
                    config=stems_config,
                    assignments=[
                        ChannelAssignment(
                            channel_name=ChannelName.PULSE1,
                            stem_ids=[0, 1] * (frame_count // 2) + ([0] if frame_count % 2 else []),
                        )
                    ],
                ),
            }
        )
        return ReconstructionData.from_reconstruction(stems_reconstruction, name="Sample")

    def test_display_hears_every_recording_on_the_channels_it_holds(
        self,
        panel_logic: ReconstructionPanelLogic,
        mock_reconstruction_manager: MagicMock,
        stems_data: ReconstructionData,
    ) -> None:
        mock_reconstruction_manager.current_reconstruction = stems_data
        stems_views = []
        panel_logic.on_stems_view_changed = stems_views.append

        panel_logic.display_reconstruction()

        assert panel_logic._stem_channels == {
            0: frozenset({ChannelName.PULSE1}),
            1: frozenset(),
        }
        assert len(stems_views) == 1
        rows = stems_views[0].stems.rows
        assert {row.key for row in rows} == {"0", "1"}
        assert all(row.channels == row.offered_channels for row in rows)
        assert stems_views[0].stems.channels_in_play == (ChannelName.PULSE1,)

    def test_a_recording_holding_no_frames_offers_no_box(
        self,
        panel_logic: ReconstructionPanelLogic,
        mock_reconstruction_manager: MagicMock,
        stems_data: ReconstructionData,
    ) -> None:
        mock_reconstruction_manager.current_reconstruction = stems_data
        stems_views = []
        panel_logic.on_stems_view_changed = stems_views.append

        panel_logic.display_reconstruction()

        rows = {row.key: row for row in stems_views[0].stems.rows}
        assert rows["0"].offered_channels == frozenset({ChannelName.PULSE1})
        assert rows["1"].offered_channels == frozenset()
        assert not rows["1"].offers_channels

    def test_a_row_stands_where_the_hierarchy_put_its_recording(
        self,
        panel_logic: ReconstructionPanelLogic,
        mock_reconstruction_manager: MagicMock,
        stems_data: ReconstructionData,
    ) -> None:
        mock_reconstruction_manager.current_reconstruction = stems_data
        stems_views = []
        panel_logic.on_stems_view_changed = stems_views.append

        panel_logic.display_reconstruction()

        rows = stems_views[0].stems.rows
        assert [(row.key, row.level, row.position) for row in rows] == [("0", 0, 0), ("1", 0, 1)]
        assert all(row.level_size == 2 and row.level_count == 1 for row in rows)

    def test_silencing_a_recording_filters_waveform_and_playback(
        self,
        panel_logic: ReconstructionPanelLogic,
        mock_reconstruction_manager: MagicMock,
        stems_data: ReconstructionData,
    ) -> None:
        mock_reconstruction_manager.current_reconstruction = stems_data
        panel_logic.display_reconstruction()
        waveform_updates = []
        audio_updates = []
        panel_logic.on_waveform_load_changed = lambda waveform, channels: waveform_updates.append(waveform)
        panel_logic.on_audio_data_changed = lambda audio: audio_updates.append(audio)

        panel_logic.set_stem_channels(0, frozenset())

        expected = stems_data.partials_for(
            panel_logic._selected_channels,
            panel_logic._stem_selection,
        )
        assert len(waveform_updates) == 1
        np.testing.assert_allclose(waveform_updates[0].partials(panel_logic._selected_channels), expected)
        assert len(audio_updates) == 1
        assert audio_updates[0] is not None
        np.testing.assert_allclose(audio_updates[0].sample, expected)

    def test_a_channel_switched_off_for_everything_mutes_its_column(
        self,
        panel_logic: ReconstructionPanelLogic,
        mock_reconstruction_manager: MagicMock,
        stems_data: ReconstructionData,
    ) -> None:
        mock_reconstruction_manager.current_reconstruction = stems_data
        panel_logic.display_reconstruction()
        stems_views = []
        panel_logic.on_stems_view_changed = stems_views.append

        panel_logic.set_selected_channels([])

        assert len(stems_views) == 1
        rows = {row.key: row for row in stems_views[0].stems.rows}
        assert stems_views[0].stems.muted_channels == frozenset({ChannelName.PULSE1})
        assert rows["0"].channels == frozenset({ChannelName.PULSE1})

    def test_export_wav_uses_the_stems_filter(
        self,
        panel_logic: ReconstructionPanelLogic,
        mock_reconstruction_manager: MagicMock,
        mock_export_service: MagicMock,
        stems_data: ReconstructionData,
        tmp_path: Path,
    ) -> None:
        mock_reconstruction_manager.current_reconstruction = stems_data
        panel_logic.display_reconstruction()
        panel_logic.set_stem_channels(0, frozenset())

        panel_logic.handle_export_wav_confirmed(tmp_path / "output.wav")

        mock_export_service.export_wav.assert_called_once()
        exported_audio = mock_export_service.export_wav.call_args.args[2]
        expected = stems_data.partials_for(
            panel_logic._selected_channels,
            panel_logic._stem_selection,
        )
        np.testing.assert_allclose(exported_audio, expected)
