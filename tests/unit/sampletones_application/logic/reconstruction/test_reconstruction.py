from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, Final, List
from unittest.mock import MagicMock

import numpy as np
import pytest

from sampletones_application.logic.reconstruction.data import ReconstructionData
from sampletones_application.logic.reconstruction.manager import ReconstructionManager
from sampletones_application.logic.reconstruction.reconstruction import (
    ReconstructionPanelLogic,
)
from sampletones_application.view_model.reconstruction.reconstruction import (
    ReconstructionPathState,
    ReconstructionViewModel,
)
from sampletones_core.audio import write_wave
from sampletones_core.configs import Config
from sampletones_core.constants.enums import AudioSourceType, GeneratorName
from sampletones_core.paths import (
    EXT_FILE_BITPHASE,
    EXT_FILE_INSTRUMENT,
    EXT_FILE_JSON,
    EXT_FILE_MODULE,
)
from sampletones_core.reconstructions import Reconstruction
from sampletones_core.trackers.format import TrackerFormat
from sampletones_core.trackers.registry import build_tracker_backends

NO_EXTENSION: Final[str] = ""


@dataclass(frozen=True)
class FormatCase:
    extension: str
    tracker_format: TrackerFormat


INSTRUMENT_FORMAT_CASES: Final[List[FormatCase]] = [
    FormatCase(extension=EXT_FILE_INSTRUMENT, tracker_format=TrackerFormat.FAMITRACKER),
    FormatCase(extension=EXT_FILE_BITPHASE, tracker_format=TrackerFormat.BITPHASE),
    FormatCase(extension=EXT_FILE_JSON, tracker_format=TrackerFormat.BITPHASE_PRESET),
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
    mock_tracker_backends: Dict[TrackerFormat, MagicMock],
) -> ReconstructionPanelLogic:
    return ReconstructionPanelLogic(
        session_manager,
        mock_reconstruction_manager,
        mock_export_service,
        mock_tracker_backends,
    )


@pytest.fixture
def mock_tracker_backends() -> Dict[TrackerFormat, MagicMock]:
    """Stands in for the real backends while declaring the scopes and extensions they do.

    The logic reads the destination's extension to pick a backend, so each stub mirrors what
    the registry's backend declares and leaves only the writing to the mock.
    """
    backends: Dict[TrackerFormat, MagicMock] = {}
    for tracker_format, backend in build_tracker_backends().items():
        stub = MagicMock()
        stub.supported_scopes = backend.supported_scopes
        stub.extension.side_effect = backend.extension
        backends[tracker_format] = stub

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
    reconstruction = reconstruction_factory().model_copy(update={"audio_filepath": source_audio})
    return ReconstructionData.from_reconstruction(reconstruction, name="Sample")


@dataclass(frozen=True)
class AudioPathCase:
    label: str
    has_filepath: bool
    has_content: bool
    expected_state: ReconstructionPathState


audio_path_cases = [
    AudioPathCase(
        "detached",
        has_filepath=False,
        has_content=False,
        expected_state=ReconstructionPathState.NOT_APPLICABLE,
    ),
    AudioPathCase(
        "recorded_but_unavailable",
        has_filepath=True,
        has_content=False,
        expected_state=ReconstructionPathState.NOT_FOUND,
    ),
    AudioPathCase(
        "available",
        has_filepath=True,
        has_content=True,
        expected_state=ReconstructionPathState.AVAILABLE,
    ),
]


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

    @pytest.mark.parametrize(
        "case",
        audio_path_cases,
        ids=lambda case: case.label,
    )
    def test_audio_path_state_follows_loaded_content(self, case: AudioPathCase) -> None:
        audio_filepath = Path("/songs/source.wav") if case.has_filepath else None
        original_audio = np.zeros(4, dtype=np.float32) if case.has_content else None

        view_model = ReconstructionPanelLogic._build_audio_path_view_model(
            audio_filepath,
            original_audio,
        )

        assert view_model.state is case.expected_state


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


class TestReconstructionPanelLogicSelectedGenerators:
    def test_set_selected_generators_updates_selection(
        self,
        panel_logic: ReconstructionPanelLogic,
        mock_reconstruction_manager: MagicMock,
        loaded_data: ReconstructionData,
    ) -> None:
        mock_reconstruction_manager.current_reconstruction = loaded_data
        panel_logic.set_selected_generators([GeneratorName.PULSE1])
        assert panel_logic._selected_generators == [GeneratorName.PULSE1]

    def test_set_selected_generators_fires_waveform_load(
        self,
        panel_logic: ReconstructionPanelLogic,
        mock_reconstruction_manager: MagicMock,
        loaded_data: ReconstructionData,
    ) -> None:
        mock_reconstruction_manager.current_reconstruction = loaded_data
        callback = MagicMock()
        panel_logic.on_waveform_load_changed = callback
        panel_logic.set_selected_generators([GeneratorName.PULSE1])
        callback.assert_called_once()

    def test_set_selected_generators_with_no_data_skips_waveform(
        self,
        panel_logic: ReconstructionPanelLogic,
    ) -> None:
        callback = MagicMock()
        panel_logic.on_waveform_load_changed = callback
        panel_logic.set_selected_generators([GeneratorName.PULSE1])
        callback.assert_not_called()


class TestReconstructionPanelLogicExportInstrument:
    def test_request_export_instrument_dialog_with_no_data_raises_assertion_error(
        self,
        panel_logic: ReconstructionPanelLogic,
    ) -> None:
        with pytest.raises(AssertionError):
            panel_logic.request_export_instrument_dialog(GeneratorName.PULSE1)

    def test_request_export_instrument_dialog_fires_dialog_callback(
        self,
        panel_logic: ReconstructionPanelLogic,
        mock_reconstruction_manager: MagicMock,
        loaded_data: ReconstructionData,
    ) -> None:
        mock_reconstruction_manager.current_reconstruction = loaded_data
        callback = MagicMock()
        panel_logic.on_open_export_instrument_dialog = callback
        panel_logic.request_export_instrument_dialog(GeneratorName.PULSE1)
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
        panel_logic.request_export_instrument_dialog(GeneratorName.PULSE1)
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
        panel_logic.request_export_instrument_dialog(GeneratorName.TRIANGLE)
        callback.assert_not_called()

    def test_request_export_instrument_dialog_sends_the_generator_to_the_dialog(
        self,
        panel_logic: ReconstructionPanelLogic,
        mock_reconstruction_manager: MagicMock,
        loaded_data: ReconstructionData,
    ) -> None:
        """The generator travels with the request, so the confirmation names it back."""
        mock_reconstruction_manager.current_reconstruction = loaded_data
        callback = MagicMock()
        panel_logic.on_open_export_instrument_dialog = callback
        panel_logic.request_export_instrument_dialog(GeneratorName.PULSE1)
        assert callback.call_args.args[2] == GeneratorName.PULSE1

    def test_handle_export_instrument_confirmed_with_no_data_does_not_export(
        self,
        panel_logic: ReconstructionPanelLogic,
        mock_export_service: MagicMock,
        tmp_path: Path,
    ) -> None:
        panel_logic.handle_export_instrument_confirmed(
            tmp_path / "instrument.fti",
            GeneratorName.PULSE1,
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
            GeneratorName.PULSE1,
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
            GeneratorName.PULSE1,
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
        mock_tracker_backends: Dict[TrackerFormat, MagicMock],
        tmp_path: Path,
        case: FormatCase,
    ) -> None:
        mock_reconstruction_manager.current_reconstruction = loaded_data
        panel_logic.handle_export_instrument_confirmed(
            tmp_path / f"instrument{case.extension}",
            GeneratorName.PULSE1,
        )
        backend = mock_export_service.export_instrument.call_args.args[1]
        assert backend is mock_tracker_backends[case.tracker_format]

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
                GeneratorName.PULSE1,
            )


class TestReconstructionPanelLogicExportInstruments:
    def test_request_export_instruments_dialog_with_no_data_raises_assertion_error(
        self,
        panel_logic: ReconstructionPanelLogic,
    ) -> None:
        with pytest.raises(AssertionError):
            panel_logic.request_export_instruments_dialog(TrackerFormat.FAMITRACKER)

    def test_request_export_instruments_dialog_fires_dialog_callback(
        self,
        panel_logic: ReconstructionPanelLogic,
        mock_reconstruction_manager: MagicMock,
        loaded_data: ReconstructionData,
    ) -> None:
        mock_reconstruction_manager.current_reconstruction = loaded_data
        callback = MagicMock()
        panel_logic.on_open_export_instruments_dialog = callback
        panel_logic.request_export_instruments_dialog(TrackerFormat.FAMITRACKER)
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
        panel_logic.request_export_instruments_dialog(TrackerFormat.FAMITRACKER)
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
        panel_logic.request_export_instruments_dialog(TrackerFormat.BITPHASE_PRESET)
        assert callback.call_args.args[2] == TrackerFormat.BITPHASE_PRESET

    def test_handle_export_instruments_confirmed_with_no_data_is_no_op(
        self,
        panel_logic: ReconstructionPanelLogic,
        mock_export_service: MagicMock,
        tmp_path: Path,
    ) -> None:
        panel_logic.handle_export_instruments_confirmed(
            tmp_path / "sample.fti",
            TrackerFormat.FAMITRACKER,
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
            TrackerFormat.FAMITRACKER,
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
            TrackerFormat.FAMITRACKER,
        )
        request = mock_export_service.export_sample.call_args.args[2]
        assert request.name == "Clap"
        assert [instrument.name for instrument in request.instruments] == ["Clap (pulse1)"]

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
        mock_tracker_backends: Dict[TrackerFormat, MagicMock],
        tmp_path: Path,
        case: FormatCase,
    ) -> None:
        """The action names the tracker, so the destination's own extension leaves the
        backend it is written through untouched.
        """
        mock_reconstruction_manager.current_reconstruction = loaded_data
        panel_logic.handle_export_instruments_confirmed(
            tmp_path / f"sample{case.extension}",
            case.tracker_format,
        )
        backend = mock_export_service.export_sample.call_args.args[1]
        assert backend is mock_tracker_backends[case.tracker_format]


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
        panel_logic._selected_generators = [GeneratorName.PULSE1]
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
    def test_no_audio_filepath_skips_locating(
        self,
        panel_logic: ReconstructionPanelLogic,
        mock_reconstruction_manager: MagicMock,
    ) -> None:
        mock_reconstruction_manager.audio_filepath = None
        panel_logic.handle_locate_original_audio()
        mock_reconstruction_manager.locate_original_audio.assert_not_called()

    def test_missing_audio_file_fires_on_locate_audio_not_found(
        self,
        panel_logic: ReconstructionPanelLogic,
        mock_reconstruction_manager: MagicMock,
        tmp_path: Path,
    ) -> None:
        missing = tmp_path / "ghost.wav"
        mock_reconstruction_manager.audio_filepath = missing
        mock_reconstruction_manager.locate_original_audio.side_effect = FileNotFoundError
        callback = MagicMock()
        panel_logic.on_locate_audio_not_found = callback
        panel_logic.handle_locate_original_audio()
        callback.assert_called_once_with(missing)
