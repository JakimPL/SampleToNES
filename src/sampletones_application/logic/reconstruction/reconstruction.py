from pathlib import Path
from typing import Callable, FrozenSet, List, Optional, Tuple

from sampletones_application.config.managers.session import SessionManager
from sampletones_application.logic.reconstruction.data import ReconstructionData
from sampletones_application.logic.reconstruction.manager import ReconstructionManager
from sampletones_application.services.export import ExportService
from sampletones_application.view_model.reconstruction.reconstruction import (
    ReconstructionPathState,
    ReconstructionPathViewModel,
    ReconstructionViewModel,
)
from sampletones_application.view_model.shared.audio_data import AudioData
from sampletones_core.constants.enums import AudioSourceType, GeneratorName
from sampletones_core.paths import EXT_FILE_INSTRUMENT
from sampletones_shared.logger import logger
from sampletones_shared.types.callback import PathCallback, VoidCallback
from sampletones_shared.utils.callbacks import CallbackMixin


class ReconstructionPanelLogic(CallbackMixin):
    def __init__(
        self,
        session_manager: SessionManager,
        reconstruction_manager: ReconstructionManager,
        export_service: ExportService,
    ) -> None:
        self._session_manager = session_manager
        self._reconstruction_manager = reconstruction_manager
        self._export_service = export_service

        self._current_audio_source: AudioSourceType = AudioSourceType.RECONSTRUCTION
        self._selected_generators: List[GeneratorName] = []
        self._pending_generator_name: Optional[GeneratorName] = None

        self.on_view_changed: Optional[Callable[[ReconstructionViewModel], None]] = None
        self.on_audio_data_changed: Optional[Callable[[Optional[AudioData]], None]] = None
        self.on_waveform_load_changed: Optional[Callable[[ReconstructionData, List[GeneratorName]], None]] = None
        self.on_waveform_update_changed: Optional[Callable[[ReconstructionData, List[GeneratorName]], None]] = None
        self.on_waveform_cleared: Optional[VoidCallback] = None
        self.on_waveform_source_changed: Optional[Callable[[AudioSourceType], None]] = None

        self.on_open_export_instrument_dialog: Optional[Callable[[str, str], None]] = None
        self.on_open_export_instruments_dialog: Optional[Callable[[str, str], None]] = None
        self.on_open_export_wav_dialog: Optional[Callable[[str, str], None]] = None

        self.on_locate_audio_missing: Optional[VoidCallback] = None
        self.on_locate_audio_not_found: Optional[PathCallback] = None

    def display_reconstruction(self) -> None:
        reconstruction_data = self._reconstruction_data
        if not reconstruction_data:
            return

        available_generators: FrozenSet[GeneratorName] = frozenset(
            reconstruction_data.reconstruction.instructions.keys()
        )
        self._selected_generators = list(available_generators)

        reconstruction_file, original_audio = self._build_path_view_models(reconstruction_data)
        self.call(
            self.on_view_changed,
            ReconstructionViewModel(
                reconstruction_loaded=True,
                available_generators=available_generators,
                audio_source_enabled=True,
                buttons_enabled=True,
                reconstruction_file=reconstruction_file,
                original_audio=original_audio,
            ),
        )
        self.call(self.on_waveform_source_changed, self._current_audio_source)
        self.call(
            self.on_waveform_load_changed,
            reconstruction_data,
            self._selected_generators,
        )
        self._emit_audio_data()

    def update_reconstruction(self) -> None:
        reconstruction_data = self._reconstruction_data
        if not reconstruction_data:
            return

        self.call(
            self.on_waveform_update_changed,
            reconstruction_data,
            self._selected_generators,
        )
        if self._current_audio_source != AudioSourceType.ORIGINAL:
            self._emit_audio_data()

    def close_reconstruction(self) -> None:
        self._current_audio_source = AudioSourceType.RECONSTRUCTION
        self._selected_generators = []
        self.call(self.on_audio_data_changed, None)
        self.call(self.on_waveform_cleared)
        empty_path = ReconstructionPathViewModel(state=ReconstructionPathState.EMPTY, path="")
        self.call(
            self.on_view_changed,
            ReconstructionViewModel(
                reconstruction_loaded=False,
                available_generators=frozenset(),
                audio_source_enabled=False,
                buttons_enabled=False,
                reconstruction_file=empty_path,
                original_audio=empty_path,
            ),
        )

    def set_audio_source(self, audio_source: AudioSourceType) -> None:
        self._current_audio_source = audio_source
        self._emit_audio_data()
        self.call(self.on_waveform_source_changed, audio_source)

    def set_selected_generators(self, generators: List[GeneratorName]) -> None:
        self._selected_generators = generators
        reconstruction_data = self._reconstruction_data
        if not reconstruction_data:
            return

        self.call(self.on_waveform_load_changed, reconstruction_data, generators)
        self._emit_audio_data()

    def request_export_instrument_dialog(self, generator_name: GeneratorName) -> None:
        reconstruction_data = self._reconstruction_data
        if not reconstruction_data:
            raise AssertionError("Expected reconstruction data to be loaded before exporting FTI")

        feature_data = reconstruction_data.feature_data
        if generator_name not in feature_data.generators:
            return

        instrument_name = f"{reconstruction_data.name} ({generator_name})"
        default_path = str(self._session_manager.get_instrument_path())

        self._pending_generator_name = generator_name
        self.call(self.on_open_export_instrument_dialog, instrument_name, default_path)

    def request_export_instruments_dialog(self) -> None:
        reconstruction_data = self._reconstruction_data
        if not reconstruction_data:
            raise AssertionError("Expected reconstruction data to be loaded before exporting FTIs")

        default_filename = reconstruction_data.name
        default_path = str(self._session_manager.get_instrument_path())

        self.call(
            self.on_open_export_instruments_dialog,
            default_filename,
            default_path,
        )

    def request_export_wav_dialog(self) -> None:
        reconstruction_data = self._reconstruction_data
        if not reconstruction_data:
            raise AssertionError("Expected reconstruction data to be loaded before exporting to WAV")

        default_filename = reconstruction_data.name
        default_path = str(self._session_manager.get_audio_path())

        self.call(self.on_open_export_wav_dialog, default_filename, default_path)

    def handle_export_instrument_confirmed(self, filepath: Path) -> None:
        if not self._reconstruction_data or not self._pending_generator_name:
            logger.warning("No reconstruction data available for FTI export")
            self._pending_generator_name = None
            return

        generator_name = self._pending_generator_name
        instrument_name = self._get_instrument_name(generator_name)
        feature = self._reconstruction_data.feature_data[generator_name]
        self._pending_generator_name = None

        self._session_manager.set_instrument_path(filepath.parent)
        self._export_service.export_instrument(filepath, instrument_name, feature)

    def handle_export_instruments_confirmed(self, directory: Path) -> None:
        reconstruction_data = self._reconstruction_data
        if not reconstruction_data:
            logger.warning("No reconstruction data available for FTIs export")
            return

        exports = [
            (
                directory / f"{self._get_instrument_name(gen_name)}{EXT_FILE_INSTRUMENT}",
                self._get_instrument_name(gen_name),
                feature,
            )
            for gen_name, feature in reconstruction_data.feature_data.generators.items()
        ]
        self._session_manager.set_instrument_path(directory.parent)
        self._export_service.export_instruments(directory, exports)

    def handle_export_wav_confirmed(self, filepath: Path) -> None:
        reconstruction_data = self._reconstruction_data
        if not reconstruction_data:
            logger.warning("No reconstruction data available for WAV export")
            return

        audio_snapshot = reconstruction_data.get_partials(self._selected_generators)
        sample_rate = reconstruction_data.reconstruction.config.sample_rate
        self._session_manager.set_audio_path(filepath)
        self._export_service.export_wav(filepath, sample_rate, audio_snapshot)

    def handle_locate_original_audio(self) -> None:
        path = self._reconstruction_manager.audio_filepath
        if path is None:
            self.call(self.on_locate_audio_missing)
            return

        try:
            self._reconstruction_manager.locate_original_audio()
        except FileNotFoundError:
            logger.warning(f"Original audio file could not be found: '{path}'")
            self.call(self.on_locate_audio_not_found, path)

    def _get_instrument_name(self, generator_name: Optional[GeneratorName] = None) -> str:
        reconstruction_data = self._reconstruction_data
        if not reconstruction_data:
            raise AssertionError("Expected reconstruction data to be present")

        filename = reconstruction_data.name
        if generator_name is None:
            return filename

        return f"{filename}_{generator_name}"

    def _emit_audio_data(self) -> None:
        audio_data = self._compute_audio_data()
        self.call(self.on_audio_data_changed, audio_data)

    def _compute_audio_data(self) -> Optional[AudioData]:
        reconstruction_data = self._reconstruction_data
        if not reconstruction_data:
            return None

        sample_rate = reconstruction_data.reconstruction.config.sample_rate
        if self._current_audio_source == AudioSourceType.ORIGINAL:
            return AudioData.from_array(reconstruction_data.original_audio, sample_rate)

        partial_approximation = reconstruction_data.get_partials(self._selected_generators)
        return AudioData.from_array(partial_approximation, sample_rate)

    def _build_path_view_models(
        self,
        reconstruction_data: ReconstructionData,
    ) -> Tuple[ReconstructionPathViewModel, ReconstructionPathViewModel]:
        """Resolves the reconstruction-file and original-audio locations for display.

        Each location is reported independently. A file-backed reconstruction knows its own file;
        a detached one (a project sample) reports not-applicable. Its source audio is available when
        it exists on this machine, not-found when the path is set but missing, and not-applicable
        when the reconstruction has been detached from its origin.
        """
        reconstruction_file = self._build_file_path_view_model(reconstruction_data.filepath)
        original_audio = self._build_audio_path_view_model(reconstruction_data.reconstruction.audio_filepath)
        return reconstruction_file, original_audio

    @staticmethod
    def _build_file_path_view_model(filepath: Optional[Path]) -> ReconstructionPathViewModel:
        if filepath is None:
            return ReconstructionPathViewModel(state=ReconstructionPathState.NOT_APPLICABLE, path="")

        return ReconstructionPathViewModel(state=ReconstructionPathState.AVAILABLE, path=str(filepath))

    @staticmethod
    def _build_audio_path_view_model(audio_filepath: Optional[Path]) -> ReconstructionPathViewModel:
        if audio_filepath is None:
            return ReconstructionPathViewModel(state=ReconstructionPathState.NOT_APPLICABLE, path="")

        if audio_filepath.exists():
            return ReconstructionPathViewModel(state=ReconstructionPathState.AVAILABLE, path=str(audio_filepath))

        return ReconstructionPathViewModel(state=ReconstructionPathState.NOT_FOUND, path="")

    @property
    def _reconstruction_data(self) -> Optional[ReconstructionData]:
        return self._reconstruction_manager.current_reconstruction
