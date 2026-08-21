from pathlib import Path
from typing import Callable, Dict, FrozenSet, List, Optional, Protocol, Tuple

import numpy as np

from sampletones_application.config.managers.session import SessionManager
from sampletones_application.logic.reconstruction.data import ReconstructionData
from sampletones_application.logic.reconstruction.manager import ReconstructionManager
from sampletones_application.view_model.reconstruction.paths.path import (
    ReconstructionPathViewModel,
)
from sampletones_application.view_model.reconstruction.paths.state import (
    ReconstructionPathState,
)
from sampletones_application.view_model.reconstruction.reconstruction import (
    ReconstructionViewModel,
)
from sampletones_application.view_model.reconstruction.stems import (
    ReconstructionStemsViewModel,
    StemViewModel,
)
from sampletones_application.view_model.shared.audio_data import AudioData
from sampletones_application.view_model.shared.waveform_data import WaveformData
from sampletones_core.configs.library import InstructionsLibraryConfig
from sampletones_core.constants.enums import AudioSourceType, ChannelName
from sampletones_core.exporters.feature import Features
from sampletones_core.exporters.naming import instrument_slice_name
from sampletones_core.exports.backend import ExportBackend
from sampletones_core.exports.extensions import format_for_extension
from sampletones_core.exports.format import ExportFormat
from sampletones_core.exports.request import InstrumentExport, SampleExport
from sampletones_core.exports.scope import ExportScope
from sampletones_shared.logger import logger
from sampletones_shared.music import Tuning
from sampletones_shared.types.callback import PathCallback, VoidCallback
from sampletones_shared.utils.callbacks import CallbackMixin
from sampletones_shared.utils.system.paths import (
    first_missing,
    get_filename,
    open_path_in_explorer,
)


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
        backend: ExportBackend,
        request: InstrumentExport,
    ) -> None: ...

    def export_sample(
        self,
        destination: Path,
        backend: ExportBackend,
        request: SampleExport,
    ) -> None: ...


class ReconstructionPanelLogic(CallbackMixin):
    def __init__(
        self,
        session_manager: SessionManager,
        reconstruction_manager: ReconstructionManager,
        export_service: ExportServiceProtocol,
        export_backends: Dict[ExportFormat, ExportBackend],
    ) -> None:
        self._session_manager = session_manager
        self._reconstruction_manager = reconstruction_manager
        self._export_service = export_service
        self._export_backends = export_backends

        self._current_audio_source: AudioSourceType = AudioSourceType.RECONSTRUCTION
        self._playing_channels: FrozenSet[ChannelName] = frozenset()
        self._selected_channels: List[ChannelName] = []
        self._available_stems: FrozenSet[int] = frozenset()
        self._selected_stems: FrozenSet[int] = frozenset()

        self.on_view_changed: Optional[Callable[[ReconstructionViewModel], None]] = None
        self.on_audio_data_changed: Optional[Callable[[Optional[AudioData]], None]] = None
        self.on_waveform_load_changed: Optional[Callable[[WaveformData, List[ChannelName]], None]] = None
        self.on_waveform_update_changed: Optional[Callable[[WaveformData, List[ChannelName]], None]] = None
        self.on_waveform_cleared: Optional[VoidCallback] = None
        self.on_waveform_source_changed: Optional[Callable[[AudioSourceType], None]] = None

        self.on_open_export_instrument_dialog: Optional[Callable[[str, str, ChannelName], None]] = None
        self.on_open_export_instruments_dialog: Optional[Callable[[str, str, ExportFormat], None]] = None
        self.on_open_export_wav_dialog: Optional[Callable[[str, str], None]] = None

        self.on_locate_audio_not_found: Optional[PathCallback] = None
        self.on_stems_view_changed: Optional[Callable[[ReconstructionStemsViewModel], None]] = None

    def display_reconstruction(self) -> None:
        reconstruction_data = self._reconstruction_data
        if not reconstruction_data:
            return

        self._playing_channels = frozenset(reconstruction_data.reconstruction.playing_channels)
        self._selected_channels = self._in_channel_order(self._playing_channels)
        self._available_stems = self._all_stem_ids(reconstruction_data)
        self._selected_stems = self._available_stems

        view_model = self._build_view_model(reconstruction_data)
        if not view_model.audio_source_enabled:
            self._current_audio_source = AudioSourceType.RECONSTRUCTION

        self.call(self.on_view_changed, view_model)
        self.call(
            self.on_stems_view_changed,
            self._build_stems_view_model(reconstruction_data),
        )
        self.call(self.on_waveform_source_changed, self._current_audio_source)
        self.call(
            self.on_waveform_load_changed,
            reconstruction_data.waveform_data(self._selected_stems),
            self._selected_channels,
        )
        self._emit_audio_data()

    def update_reconstruction(self) -> None:
        reconstruction_data = self._reconstruction_data
        if not reconstruction_data:
            return

        self._adopt_playing_channels(frozenset(reconstruction_data.reconstruction.playing_channels))
        self._adopt_selected_stems(self._all_stem_ids(reconstruction_data))

        self.call(self.on_view_changed, self._build_view_model(reconstruction_data))
        self.call(
            self.on_stems_view_changed,
            self._build_stems_view_model(reconstruction_data),
        )
        self.call(
            self.on_waveform_update_changed,
            reconstruction_data.waveform_data(self._selected_stems),
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
        self._available_stems = frozenset()
        self._selected_stems = frozenset()
        self.call(self.on_audio_data_changed, None)
        self.call(self.on_waveform_cleared)
        self.call(
            self.on_stems_view_changed,
            ReconstructionStemsViewModel(
                reconstruction_loaded=False,
                stems=(),
            ),
        )
        empty_path = ReconstructionPathViewModel(
            state=ReconstructionPathState.EMPTY,
            paths=(),
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
            reconstruction_data.waveform_data(self._selected_stems),
            channels,
        )
        self._emit_audio_data()

    def set_selected_stems(self, stem_ids: FrozenSet[int]) -> None:
        """Adopts the reader's stem choice and re-answers playback and the waveform.

        The choice is listening state, so it filters what plays and what the waveform
        shows without touching the document.
        """
        self._selected_stems = stem_ids
        reconstruction_data = self._reconstruction_data
        if not reconstruction_data:
            return

        self.call(
            self.on_stems_view_changed,
            self._build_stems_view_model(reconstruction_data),
        )
        self.call(
            self.on_waveform_load_changed,
            reconstruction_data.waveform_data(self._selected_stems),
            self._selected_channels,
        )
        self._emit_audio_data()

    def _adopt_selected_stems(self, stem_ids: FrozenSet[int]) -> None:
        """Carries the reader's stem choice across an edit.

        A stem that keeps existing keeps whatever the reader chose for it, and one
        appearing for the first time joins selected, so a deliberate choice survives
        while the new stems' content is heard.
        """
        selected = (set(self._selected_stems) & stem_ids) | (stem_ids - self._available_stems)
        self._available_stems = stem_ids
        self._selected_stems = frozenset(selected)

    @staticmethod
    def _all_stem_ids(
        reconstruction_data: ReconstructionData,
    ) -> FrozenSet[int]:
        return frozenset(entry.id for entry in reconstruction_data.reconstruction.stems_data.config.entries)

    def _build_stems_view_model(
        self,
        reconstruction_data: ReconstructionData,
    ) -> ReconstructionStemsViewModel:
        reconstruction = reconstruction_data.reconstruction
        stems_data = reconstruction.stems_data
        source_paths = reconstruction.audio_filepath
        if not source_paths:
            return ReconstructionStemsViewModel(
                reconstruction_loaded=True,
                stems=(),
            )

        assigned_stem_ids = {stem_id for stem_ids in stems_data.assignments_by_channel.values() for stem_id in stem_ids}
        rows = tuple(
            StemViewModel(
                stem_id=entry.id,
                label=source_paths[index].name,
                channels=tuple(entry.channels),
                enabled=entry.id in assigned_stem_ids,
                selected=entry.id in self._selected_stems,
            )
            for index, entry in enumerate(stems_data.config.entries)
        )
        return ReconstructionStemsViewModel(
            reconstruction_loaded=True,
            stems=rows,
            hierarchy_mode=stems_data.config.hierarchy.mode,
            channel_cap=stems_data.config.channel_cap,
        )

    def request_export_instrument_dialog(
        self,
        channel_name: ChannelName,
    ) -> None:
        """Asks for the destination one channel slice is written to.

        Every format able to write a single slice is offered at once, so the channel travels
        with the request to the dialog and back. The suggestion is the instrument's name on its
        own, leaving the format to the dialog's file-type selector and to any extension typed
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
        export_format: ExportFormat,
    ) -> None:
        """Asks for the destination the loaded reconstruction's slices are named after.

        The format comes from the action that was chosen, so the dialog offers that
        format's file type alone and the suggestion already ends in its extension.

        Args:
            export_format: The format the slices are written in.
        """
        reconstruction_data = self._reconstruction_data
        if not reconstruction_data:
            raise AssertionError("Expected reconstruction data to be loaded before exporting instruments")

        default_path = str(self._session_manager.get_instrument_path())
        extension = self._export_backends[export_format].extension(ExportScope.SAMPLE)

        self.call(
            self.on_open_export_instruments_dialog,
            get_filename(reconstruction_data.name, extension),
            default_path,
            export_format,
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

        The extension picks the format the slice is written in, and the instrument carries
        the name the destination was saved under, so renaming the file in the dialog renames
        the instrument the file carries.

        Args:
            filepath: The destination the dialog was confirmed with.
            channel_name: The channel whose slice is written.
        """
        reconstruction_data = self._reconstruction_data
        if not reconstruction_data:
            logger.warning("No reconstruction data available for instrument export")
            return

        export_format = self._export_format(filepath, ExportScope.INSTRUMENT)
        feature = reconstruction_data.feature_data[channel_name]

        self._session_manager.set_instrument_path(filepath.parent)
        self._export_service.export_instrument(
            filepath,
            self._export_backends[export_format],
            self._instrument_export(channel_name, feature, filepath.stem),
        )

    def handle_export_instruments_confirmed(
        self,
        destination: Path,
        export_format: ExportFormat,
    ) -> None:
        """Writes the slice of every playing channel of the loaded reconstruction to ``destination``.

        The destination names the batch: each slice takes its channel suffix from the stem,
        so a format gathering the whole reconstruction into one document writes it there while
        one keeping an instrument per file writes its slices beside it. A channel standing by
        describes no frame and is written nowhere.

        Args:
            destination: The file the export was confirmed with.
            export_format: The format the slices are written in.
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
            tuning=self._tuning(),
        )
        self._session_manager.set_instrument_path(destination.parent)
        self._export_service.export_sample(
            destination,
            self._export_backends[export_format],
            request,
        )

    def _export_format(
        self,
        destination: Path,
        scope: ExportScope,
    ) -> ExportFormat:
        """Reads the export format out of the destination's extension.

        A save dialog answers with one of the extensions it offered, and an export offers the
        types its own formats write, so every destination reaching here names a format.

        Args:
            destination: The destination the export was confirmed with.
            scope: The scope about to be written.

        Returns:
            ExportFormat: The format to write in.

        Raises:
            ValueError: If no format able to express ``scope`` claims the extension.
        """
        export_format = format_for_extension(self._export_backends, scope, destination.suffix)
        if export_format is None:
            raise ValueError(f"No export format writes '{destination.suffix}' for a {scope} export")

        return export_format

    def _instrument_export(
        self,
        channel_name: ChannelName,
        feature: Features,
        name: str,
    ) -> InstrumentExport:
        """Packages one channel slice under ``name`` for an export backend.

        A reconstruction has no loop flag of its own — that belongs to a sample placed in
        a project — so the instrument plays its envelopes once.
        """
        return InstrumentExport(
            name=name,
            channel=channel_name,
            features=feature,
            loop=False,
            nes_frequency=self._nes_frequency(),
            tuning=self._tuning(),
        )

    def _nes_frequency(self) -> int:
        """The rate the loaded reconstruction's envelopes advance at, in Hz."""
        return self._library_config().nes_frequency

    def _tuning(self) -> Tuning:
        """Where concert pitch sat for the loaded reconstruction.

        A backend sounding the export on its own — the console player's driver reaching pitches
        through timer values — measures them from the tuning the reconstruction was built with,
        which keeps what it plays in tune with the reconstruction's own approximation.
        """
        return self._library_config().tuning

    def _library_config(self) -> InstructionsLibraryConfig:
        """The instruction settings the loaded reconstruction was built with.

        Raises:
            AssertionError: If no reconstruction is loaded.
        """
        reconstruction_data = self._reconstruction_data
        if not reconstruction_data:
            raise AssertionError("Expected reconstruction data to be present")

        return reconstruction_data.config.library

    def handle_export_wav_confirmed(self, filepath: Path) -> None:
        reconstruction_data = self._reconstruction_data
        if not reconstruction_data:
            logger.warning("No reconstruction data available for WAV export")
            return

        audio_snapshot = reconstruction_data.partials_for(
            self._selected_channels,
            self._selected_stems,
        )
        sample_rate = reconstruction_data.reconstruction.config.sample_rate
        self._session_manager.set_audio_path(filepath)
        self._export_service.export_wav(filepath, sample_rate, audio_snapshot)

    def handle_locate_original_audio(self) -> None:
        if not self._reconstruction_manager.source_paths:
            return

        try:
            self._reconstruction_manager.locate_original_audio()
        except FileNotFoundError:
            missing_path = first_missing(self._reconstruction_manager.source_paths)
            if missing_path is None:
                raise

            logger.warning(f"Original audio file could not be found: '{logger.format_path(missing_path)}'")
            self.call(self.on_locate_audio_not_found, missing_path)

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
            if reconstruction_data.original_audio is None:
                return None

            selected_original_audio = reconstruction_data.original_mix_for(self._selected_stems)
            return AudioData.from_array(selected_original_audio, sample_rate)

        partial_approximation = reconstruction_data.partials_for(
            self._selected_channels,
            self._selected_stems,
        )
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
                paths=(),
            )

        return ReconstructionPathViewModel(
            state=ReconstructionPathState.AVAILABLE,
            paths=(str(filepath),),
        )

    @staticmethod
    def _build_audio_path_view_model(
        source_paths: Tuple[Path, ...],
        original_audio: Optional[np.ndarray],
    ) -> ReconstructionPathViewModel:
        """Reports the original-audio location, treating a recorded path with unusable content
        the same as a missing one, so the source toggle and waveform agree with what actually loaded."""
        if source_paths and original_audio is None:
            return ReconstructionPathViewModel(
                state=ReconstructionPathState.NOT_FOUND,
                paths=(),
            )

        return ReconstructionPathViewModel(
            state=ReconstructionPathState.from_source_paths(source_paths),
            paths=tuple(str(path) for path in source_paths),
        )

    @property
    def _reconstruction_data(self) -> Optional[ReconstructionData]:
        return self._reconstruction_manager.current_reconstruction
