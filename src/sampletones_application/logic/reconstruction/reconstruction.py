from pathlib import Path
from typing import Callable, Dict, FrozenSet, List, Optional, Protocol, Tuple

import numpy as np

from sampletones_application.config.managers.session import SessionManager
from sampletones_application.logic.reconstruction.data import ReconstructionData
from sampletones_application.logic.reconstruction.manager import ReconstructionManager
from sampletones_application.view_model.reconstruction.reconstruction import (
    ReconstructionPathState,
    ReconstructionPathViewModel,
    ReconstructionViewModel,
)
from sampletones_application.view_model.shared.audio_data import AudioData
from sampletones_application.view_model.shared.waveform_data import WaveformData
from sampletones_core.constants.enums import AudioSourceType, ChannelName
from sampletones_core.exporters.feature import Features
from sampletones_core.exporters.naming import instrument_slice_name
from sampletones_core.trackers.backend import TrackerBackend
from sampletones_core.trackers.extensions import format_for_extension
from sampletones_core.trackers.format import TrackerFormat
from sampletones_core.trackers.request import InstrumentExport, SampleExport
from sampletones_core.trackers.scope import ExportScope
from sampletones_shared.logger import logger
from sampletones_shared.types.callback import PathCallback, VoidCallback
from sampletones_shared.utils.callbacks import CallbackMixin
from sampletones_shared.utils.system.paths import get_filename, open_path_in_explorer


class ExportServiceProtocol(Protocol):
    """The slice of the export service the reconstruction panel logic drives.

    Typing the collaborator structurally keeps the logic layer independent of
    the service implementation; the composition root supplies the real service.
    """

    def export_wav(
        self,
        filepath: Path,
        sample_rate: int,
        audio: np.ndarray,
    ) -> None: ...

    def export_instrument(
        self,
        destination: Path,
        backend: TrackerBackend,
        request: InstrumentExport,
    ) -> None: ...

    def export_sample(
        self,
        destination: Path,
        backend: TrackerBackend,
        request: SampleExport,
    ) -> None: ...


class ReconstructionPanelLogic(CallbackMixin):
    def __init__(
        self,
        session_manager: SessionManager,
        reconstruction_manager: ReconstructionManager,
        export_service: ExportServiceProtocol,
        tracker_backends: Dict[TrackerFormat, TrackerBackend],
    ) -> None:
        self._session_manager = session_manager
        self._reconstruction_manager = reconstruction_manager
        self._export_service = export_service
        self._tracker_backends = tracker_backends

        self._current_audio_source: AudioSourceType = AudioSourceType.RECONSTRUCTION
        self._playing_channels: FrozenSet[ChannelName] = frozenset()
        self._selected_channels: List[ChannelName] = []

        self.on_view_changed: Optional[Callable[[ReconstructionViewModel], None]] = None
        self.on_audio_data_changed: Optional[Callable[[Optional[AudioData]], None]] = None
        self.on_waveform_load_changed: Optional[Callable[[WaveformData, List[ChannelName]], None]] = None
        self.on_waveform_update_changed: Optional[Callable[[WaveformData, List[ChannelName]], None]] = None
        self.on_waveform_cleared: Optional[VoidCallback] = None
        self.on_waveform_source_changed: Optional[Callable[[AudioSourceType], None]] = None

        self.on_open_export_instrument_dialog: Optional[Callable[[str, str, ChannelName], None]] = None
        self.on_open_export_instruments_dialog: Optional[Callable[[str, str, TrackerFormat], None]] = None
        self.on_open_export_wav_dialog: Optional[Callable[[str, str], None]] = None

        self.on_locate_audio_not_found: Optional[PathCallback] = None

    def display_reconstruction(self) -> None:
        reconstruction_data = self._reconstruction_data
        if not reconstruction_data:
            return

        self._playing_channels = frozenset(reconstruction_data.reconstruction.playing_channels)
        self._selected_channels = self._in_channel_order(self._playing_channels)

        view_model = self._build_view_model(reconstruction_data)
        if not view_model.audio_source_enabled:
            self._current_audio_source = AudioSourceType.RECONSTRUCTION

        self.call(self.on_view_changed, view_model)
        self.call(self.on_waveform_source_changed, self._current_audio_source)
        self.call(
            self.on_waveform_load_changed,
            reconstruction_data.waveform_data(),
            self._selected_channels,
        )
        self._emit_audio_data()

    def update_reconstruction(self) -> None:
        reconstruction_data = self._reconstruction_data
        if not reconstruction_data:
            return

        self._adopt_playing_channels(frozenset(reconstruction_data.reconstruction.playing_channels))

        self.call(self.on_view_changed, self._build_view_model(reconstruction_data))
        self.call(
            self.on_waveform_update_changed,
            reconstruction_data.waveform_data(),
            self._selected_channels,
        )
        if self._current_audio_source != AudioSourceType.ORIGINAL:
            self._emit_audio_data()

    def _adopt_playing_channels(
        self,
        playing_channels: FrozenSet[ChannelName],
    ) -> None:
        """Carries the reader's choice of channels across an edit.

        An edit puts a channel in play or takes it out. A channel that keeps playing keeps
        whatever the reader chose for it, and one gaining its first frame joins the waveform,
        so the checkboxes report what plays while a deliberate choice survives.
        """
        selected = (set(self._selected_channels) & playing_channels) | (playing_channels - self._playing_channels)
        self._playing_channels = playing_channels
        self._selected_channels = self._in_channel_order(frozenset(selected))

    @staticmethod
    def _in_channel_order(channels: FrozenSet[ChannelName]) -> List[ChannelName]:
        return [channel_name for channel_name in ChannelName.items() if channel_name in channels]

    def _build_view_model(
        self,
        reconstruction_data: ReconstructionData,
    ) -> ReconstructionViewModel:
        reconstruction_file, original_audio = self._build_path_view_models(reconstruction_data)
        return ReconstructionViewModel(
            reconstruction_loaded=True,
            playing_channels=self._playing_channels,
            selected_channels=frozenset(self._selected_channels),
            reconstruction_file=reconstruction_file,
            original_audio=original_audio,
        )

    def close_reconstruction(self) -> None:
        self._current_audio_source = AudioSourceType.RECONSTRUCTION
        self._playing_channels = frozenset()
        self._selected_channels = []
        self.call(self.on_audio_data_changed, None)
        self.call(self.on_waveform_cleared)
        empty_path = ReconstructionPathViewModel(
            state=ReconstructionPathState.EMPTY,
            path="",
        )
        self.call(
            self.on_view_changed,
            ReconstructionViewModel(
                reconstruction_loaded=False,
                playing_channels=frozenset(),
                selected_channels=frozenset(),
                reconstruction_file=empty_path,
                original_audio=empty_path,
            ),
        )

    def set_audio_source(self, audio_source: AudioSourceType) -> None:
        self._current_audio_source = audio_source
        self._emit_audio_data()
        self.call(self.on_waveform_source_changed, audio_source)

    def set_selected_channels(self, channels: List[ChannelName]) -> None:
        self._selected_channels = channels
        reconstruction_data = self._reconstruction_data
        if not reconstruction_data:
            return

        self.call(
            self.on_waveform_load_changed,
            reconstruction_data.waveform_data(),
            channels,
        )
        self._emit_audio_data()

    def request_export_instrument_dialog(
        self,
        channel_name: ChannelName,
    ) -> None:
        """Asks for the destination one channel slice is written to.

        Every tracker able to write a single slice is offered at once, so the channel travels
        with the request to the dialog and back. The suggestion is the instrument's name on its
        own, leaving the tracker to the dialog's file-type selector and to any extension typed
        over it.

        Args:
            channel_name: The channel whose slice is written.
        """
        reconstruction_data = self._reconstruction_data
        if not reconstruction_data:
            raise AssertionError("Expected reconstruction data to be loaded before exporting an instrument")

        if channel_name not in reconstruction_data.reconstruction.playing_channels:
            return

        instrument_name = self._get_instrument_name(channel_name)
        default_path = str(self._session_manager.get_instrument_path())

        self.call(
            self.on_open_export_instrument_dialog,
            instrument_name,
            default_path,
            channel_name,
        )

    def request_export_instruments_dialog(
        self,
        tracker_format: TrackerFormat,
    ) -> None:
        """Asks for the destination the loaded reconstruction's slices are named after.

        The tracker comes from the action that was chosen, so the dialog offers that
        tracker's file type alone and the suggestion already ends in its extension.

        Args:
            tracker_format: The tracker the slices are written for.
        """
        reconstruction_data = self._reconstruction_data
        if not reconstruction_data:
            raise AssertionError("Expected reconstruction data to be loaded before exporting instruments")

        default_path = str(self._session_manager.get_instrument_path())
        extension = self._tracker_backends[tracker_format].extension(ExportScope.SAMPLE)

        self.call(
            self.on_open_export_instruments_dialog,
            get_filename(reconstruction_data.name, extension),
            default_path,
            tracker_format,
        )

    def request_export_wav_dialog(self) -> None:
        reconstruction_data = self._reconstruction_data
        if not reconstruction_data:
            raise AssertionError("Expected reconstruction data to be loaded before exporting to WAV")

        default_filename = reconstruction_data.name
        default_path = str(self._session_manager.get_audio_path())

        self.call(self.on_open_export_wav_dialog, default_filename, default_path)

    def handle_export_instrument_confirmed(
        self,
        filepath: Path,
        channel_name: ChannelName,
    ) -> None:
        """Writes the ``channel_name`` slice of the loaded reconstruction to ``filepath``.

        The extension picks the tracker the slice is written for, and the instrument carries
        the name the destination was saved under, so renaming the file in the dialog renames
        the instrument the tracker lists.

        Args:
            filepath: The destination the dialog was confirmed with.
            channel_name: The channel whose slice is written.
        """
        reconstruction_data = self._reconstruction_data
        if not reconstruction_data:
            logger.warning("No reconstruction data available for instrument export")
            return

        tracker_format = self._tracker_format(filepath, ExportScope.INSTRUMENT)
        feature = reconstruction_data.feature_data[channel_name]

        self._session_manager.set_instrument_path(filepath.parent)
        self._export_service.export_instrument(
            filepath,
            self._tracker_backends[tracker_format],
            self._instrument_export(channel_name, feature, filepath.stem),
        )

    def handle_export_instruments_confirmed(
        self,
        destination: Path,
        tracker_format: TrackerFormat,
    ) -> None:
        """Writes the slice of every playing channel of the loaded reconstruction to ``destination``.

        The destination names the batch: each slice takes its channel suffix from the stem,
        so a format gathering the whole reconstruction into one document writes it there while
        one keeping an instrument per file writes its slices beside it. A channel standing by
        describes no frame and is written nowhere.

        Args:
            destination: The file the export was confirmed with.
            tracker_format: The tracker the slices are written for.
        """
        reconstruction_data = self._reconstruction_data
        if not reconstruction_data:
            logger.warning("No reconstruction data available for instruments export")
            return

        base_name = destination.stem
        request = SampleExport(
            name=base_name,
            instruments=tuple(
                self._instrument_export(
                    channel_name,
                    feature,
                    instrument_slice_name(base_name, channel_name),
                )
                for channel_name, feature in reconstruction_data.feature_data.channels.items()
                if feature.has_frames
            ),
            nes_frequency=self._nes_frequency(),
        )
        self._session_manager.set_instrument_path(destination.parent)
        self._export_service.export_sample(
            destination,
            self._tracker_backends[tracker_format],
            request,
        )

    def _tracker_format(
        self,
        destination: Path,
        scope: ExportScope,
    ) -> TrackerFormat:
        """Reads the tracker format out of the destination's extension.

        A save dialog answers with one of the extensions it offered, and an export offers the
        types its own formats write, so every destination reaching here names a format.

        Args:
            destination: The destination the export was confirmed with.
            scope: The scope about to be written.

        Returns:
            TrackerFormat: The format to write in.

        Raises:
            ValueError: If no format able to express ``scope`` claims the extension.
        """
        tracker_format = format_for_extension(self._tracker_backends, scope, destination.suffix)
        if tracker_format is None:
            raise ValueError(f"No tracker format writes '{destination.suffix}' for a {scope} export")

        return tracker_format

    def _instrument_export(
        self,
        channel_name: ChannelName,
        feature: Features,
        name: str,
    ) -> InstrumentExport:
        """Packages one channel slice under ``name`` for a tracker backend.

        A reconstruction has no loop flag of its own — that belongs to a sample placed in
        a project — so the instrument plays its envelopes once.
        """
        return InstrumentExport(
            name=name,
            channel=channel_name,
            features=feature,
            loop=False,
            nes_frequency=self._nes_frequency(),
        )

    def _nes_frequency(self) -> int:
        """The rate the loaded reconstruction's envelopes advance at, in Hz."""
        reconstruction_data = self._reconstruction_data
        if not reconstruction_data:
            raise AssertionError("Expected reconstruction data to be present")

        return reconstruction_data.config.library.nes_frequency

    def handle_export_wav_confirmed(self, filepath: Path) -> None:
        reconstruction_data = self._reconstruction_data
        if not reconstruction_data:
            logger.warning("No reconstruction data available for WAV export")
            return

        audio_snapshot = reconstruction_data.get_partials(self._selected_channels)
        sample_rate = reconstruction_data.reconstruction.config.sample_rate
        self._session_manager.set_audio_path(filepath)
        self._export_service.export_wav(filepath, sample_rate, audio_snapshot)

    def handle_locate_original_audio(self) -> None:
        path = self._reconstruction_manager.audio_filepath
        if path is None:
            return

        try:
            self._reconstruction_manager.locate_original_audio()
        except FileNotFoundError:
            logger.warning(f"Original audio file could not be found: '{logger.format_path(path)}'")
            self.call(self.on_locate_audio_not_found, path)

    def open_reconstruction_in_explorer(self) -> None:
        """Reveals the loaded reconstruction's own file in the OS file manager."""
        filepath = self._reconstruction_manager.filepath
        if filepath is None:
            return

        open_path_in_explorer(filepath)

    def _get_instrument_name(self, channel_name: ChannelName) -> str:
        """Names the loaded reconstruction's slice for one channel."""
        reconstruction_data = self._reconstruction_data
        if not reconstruction_data:
            raise AssertionError("Expected reconstruction data to be present")

        return instrument_slice_name(reconstruction_data.name, channel_name)

    def _emit_audio_data(self) -> None:
        audio_data = self._compute_audio_data()
        self.call(self.on_audio_data_changed, audio_data)

    def _compute_audio_data(self) -> Optional[AudioData]:
        reconstruction_data = self._reconstruction_data
        if not reconstruction_data:
            return None

        sample_rate = reconstruction_data.reconstruction.config.sample_rate
        if self._current_audio_source == AudioSourceType.ORIGINAL:
            original_audio = reconstruction_data.original_audio
            if original_audio is None:
                return None

            return AudioData.from_array(original_audio, sample_rate)

        partial_approximation = reconstruction_data.get_partials(self._selected_channels)
        return AudioData.from_array(partial_approximation, sample_rate)

    def _build_path_view_models(
        self,
        reconstruction_data: ReconstructionData,
    ) -> Tuple[ReconstructionPathViewModel, ReconstructionPathViewModel]:
        """Resolves the reconstruction-file and original-audio locations for display.

        Each location is reported independently. A file-backed reconstruction knows its own file;
        a detached one (a project sample) reports not-applicable. Its source audio is available when
        the recorded file loaded, not-found when a path is recorded yet its content is unavailable,
        and not-applicable when the reconstruction has been detached from its origin.
        """
        reconstruction_file = self._build_file_path_view_model(reconstruction_data.filepath)
        original_audio = self._build_audio_path_view_model(
            reconstruction_data.reconstruction.audio_filepath,
            reconstruction_data.original_audio,
        )
        return reconstruction_file, original_audio

    @staticmethod
    def _build_file_path_view_model(
        filepath: Optional[Path],
    ) -> ReconstructionPathViewModel:
        if filepath is None:
            return ReconstructionPathViewModel(
                state=ReconstructionPathState.NOT_APPLICABLE,
                path="",
            )

        return ReconstructionPathViewModel(
            state=ReconstructionPathState.AVAILABLE,
            path=str(filepath),
        )

    @staticmethod
    def _build_audio_path_view_model(
        audio_filepath: Optional[Path],
        original_audio: Optional[np.ndarray],
    ) -> ReconstructionPathViewModel:
        """Reports the original-audio location, treating a recorded path with unusable content
        the same as a missing one, so the source toggle and waveform agree with what actually loaded."""
        if audio_filepath is None:
            return ReconstructionPathViewModel(
                state=ReconstructionPathState.NOT_APPLICABLE,
                path="",
            )

        if original_audio is None:
            return ReconstructionPathViewModel(
                state=ReconstructionPathState.NOT_FOUND,
                path="",
            )

        return ReconstructionPathViewModel(
            state=ReconstructionPathState.AVAILABLE,
            path=str(audio_filepath),
        )

    @property
    def _reconstruction_data(self) -> Optional[ReconstructionData]:
        return self._reconstruction_manager.current_reconstruction
