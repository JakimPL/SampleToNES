from pathlib import Path
from typing import Callable, Dict, Optional, Tuple

import dearpygui.dearpygui as dpg

from sampletones_application.categories.export import ExportMessages
from sampletones_application.categories.hierarchy import Page, Panel, TextType
from sampletones_application.categories.manager import LanguageManager
from sampletones_application.categories.trackers import (
    INSTRUMENT_EXPORT_FORMATS,
    TRACKER_INSTRUMENT_FILTERS,
)
from sampletones_application.config.managers.config import ConfigManager
from sampletones_application.config.managers.session import SessionManager
from sampletones_application.coordinators.original_audio import OriginalAudioLocator
from sampletones_application.coordinators.playback.guard import GuardedPlayer
from sampletones_application.coordinators.playback.protocol import AudioPlayerProtocol
from sampletones_application.logic.reconstruction.browser import BrowserLogic
from sampletones_application.logic.reconstruction.browser_manager import BrowserManager
from sampletones_application.logic.reconstruction.instruments import (
    OnReconstructionInstrumentUpdatedCallback,
    ReconstructionInstrumentsLogic,
)
from sampletones_application.logic.reconstruction.manager import ReconstructionManager
from sampletones_application.logic.reconstruction.reconstruction import (
    ReconstructionPanelLogic,
)
from sampletones_application.logic.shared.player import PlayerLogic
from sampletones_application.logic.shared.tree import TreeLogic
from sampletones_application.parameters.reconstruction import (
    ReconstructionTabParameters,
)
from sampletones_application.services.export.error import ExportError
from sampletones_application.services.export.kind import ExportKind
from sampletones_application.services.export.result import ExportResult
from sampletones_application.services.export.service import ExportService
from sampletones_application.services.export.success import ExportSuccess
from sampletones_application.tags.compose import compose_tag
from sampletones_application.tags.general import (
    SUF_PANEL_CENTER,
    SUF_PANEL_LEFT,
    SUF_PANEL_RIGHT,
    TAG_GLOBAL_TAB_RECONSTRUCTION,
    TAG_GLOBAL_TABS,
    TAG_GLOBAL_THEME_PANEL_GROUND,
    TAG_GLOBAL_THEME_PANEL_SURFACE,
)
from sampletones_application.tags.reconstructions import (
    TAG_RECONSTRUCTIONS_BROWSER_DIALOG_REMOVE_DIRECTORY_CONFIRMATION,
    TAG_RECONSTRUCTIONS_BROWSER_DIALOG_REMOVE_RECONSTRUCTION_CONFIRMATION,
    TAG_RECONSTRUCTIONS_BROWSER_PANEL,
    TAG_RECONSTRUCTIONS_INSTRUMENTS_PANEL,
    TAG_RECONSTRUCTIONS_RECONSTRUCTION_PANEL_AUDIO,
    TAG_RECONSTRUCTIONS_RECONSTRUCTION_PANEL_PLOT,
)
from sampletones_application.ui.elements.layout.columns import ColumnSpec, TabColumns
from sampletones_application.ui.elements.layout.responsive import expanded_side_width
from sampletones_application.ui.elements.status import GUIStatusBar
from sampletones_application.ui.panels.reconstruction.audio import (
    GUIReconstructionAudioPanel,
)
from sampletones_application.ui.panels.reconstruction.browser import GUIBrowserPanel
from sampletones_application.ui.panels.reconstruction.instruments.instruments import (
    GUIReconstructionInstrumentsPanel,
)
from sampletones_application.ui.panels.reconstruction.plot import (
    GUIReconstructionPlotPanel,
)
from sampletones_application.utils.file_dialogs.api import save_file_dialog
from sampletones_application.utils.file_dialogs.filter import FileFilter
from sampletones_application.utils.file_dialogs.result import ignore_none_path
from sampletones_application.utils.gui.dialogs import DialogsRenderer
from sampletones_application.utils.gui.dpg import dpg_configure_item
from sampletones_application.utils.gui.frame import FrameCallbackManager
from sampletones_application.view_model.reconstruction.reconstruction import (
    ReconstructionViewModel,
)
from sampletones_application.view_model.shared.audio_data import AudioData
from sampletones_core.audio import AudioDeviceManager
from sampletones_core.constants.enums import GeneratorName
from sampletones_core.exporters.truncation import EnvelopeTruncation
from sampletones_core.paths import EXT_FILE_WAVE
from sampletones_core.trackers.backend import TrackerBackend
from sampletones_core.trackers.format import TrackerFormat
from sampletones_core.trackers.scope import ExportScope
from sampletones_shared.exceptions import (
    DeserializationError,
    IncompatibleReconstructionVersionError,
    InvalidMetadataError,
    InvalidReconstructionError,
    InvalidReconstructionValuesError,
    LoadReconstructionError,
)
from sampletones_shared.logger import logger
from sampletones_shared.types.callback import PathCallback, VoidCallback

_LEFT_COLUMN_TAG = compose_tag(TAG_GLOBAL_TAB_RECONSTRUCTION, SUF_PANEL_LEFT)
_CENTER_COLUMN_TAG = compose_tag(TAG_GLOBAL_TAB_RECONSTRUCTION, SUF_PANEL_CENTER)
_RIGHT_COLUMN_TAG = compose_tag(TAG_GLOBAL_TAB_RECONSTRUCTION, SUF_PANEL_RIGHT)


class ReconstructionTabCoordinator:
    def __init__(
        self,
        config_manager: ConfigManager,
        session_manager: SessionManager,
        audio_device_manager: AudioDeviceManager,
        reconstruction_manager: ReconstructionManager,
        browser_manager: BrowserManager,
        export_service: ExportService,
        tracker_backends: Dict[TrackerFormat, TrackerBackend],
        on_load_reconstruction_with_confirmation: Callable[[Optional[Path]], None],
        on_reconstruct_file: VoidCallback,
        on_reconstruct_directory: VoidCallback,
        on_change_audio_state: VoidCallback,
        on_reconstruction_instrument_updated: OnReconstructionInstrumentUpdatedCallback,
        is_operation_active: Callable[[], bool],
        original_audio_locator: OriginalAudioLocator,
        *,
        layout: ReconstructionTabParameters,
        language_manager: LanguageManager,
        dialogs: DialogsRenderer,
        status_bar: GUIStatusBar,
    ) -> None:
        self._language_manager = language_manager
        self._reconstruction_manager = reconstruction_manager
        self._session_manager = session_manager
        self._tracker_backends = tracker_backends
        self._dialogs = dialogs
        self._original_audio_locator = original_audio_locator

        self._geometry = layout.geometry
        self._side_panel_count: int
        self._instruments_width = layout.right_column_width
        self._right_height = layout.right_column_height
        self._lbl_remove = language_manager["global.dialog.label.remove"]

        self._msg_load_error = language_manager["reconstructions.browser.message.load_error"]
        self._export_messages = ExportMessages.build(language_manager)
        self._instrument_filter_names: Dict[TrackerFormat, str] = {
            tracker_format: language_manager[
                Page.GLOBAL,
                Panel.DIALOG,
                TextType.FILTER,
                element,
            ]
            for tracker_format, element in TRACKER_INSTRUMENT_FILTERS.items()
        }

        self._browser_logic: BrowserLogic = BrowserLogic(
            config_manager,
            browser_manager,
        )
        self._browser_tree_logic: TreeLogic = TreeLogic(
            session_manager,
            audio_device_manager,
            scheduling=layout.scheduling,
        )
        self._browser_panel: GUIBrowserPanel = GUIBrowserPanel(
            self._browser_logic.tree,
            self._browser_tree_logic,
            scheduling=layout.scheduling,
            language_manager=language_manager,
            status_bar=status_bar,
            colors=layout.tree_colors,
            is_operation_active=is_operation_active,
            initial_collapsed=session_manager.is_card_collapsed(TAG_RECONSTRUCTIONS_BROWSER_PANEL),
        )
        self._browser_tree_logic.on_lock_state_changed = self._browser_panel.set_tree_enabled
        self._browser_tree_logic.on_favorite_changed = self._browser_panel.update_favorite_indicator
        self._browser_tree_logic.on_search_update_needed = self._browser_panel.update_tree_visibility
        self._browser_tree_logic.on_autoplay_error = self._on_browser_autoplay_error
        self._browser_panel.set_collapse_handler(self._on_browser_collapse_changed)
        self._reconstruction_player_logic = PlayerLogic(
            audio_device_manager,
            on_change_audio_state,
        )
        self._guarded_player = GuardedPlayer(
            self._reconstruction_player_logic,
            dialogs=dialogs,
            error_message=language_manager["global.player.message.audio_playback_error"],
        )
        self._reconstruction_audio_panel: GUIReconstructionAudioPanel = GUIReconstructionAudioPanel(
            path_colors=layout.path_colors,
            path_status_color=layout.path_status_color,
            initial_collapsed=session_manager.is_card_collapsed(TAG_RECONSTRUCTIONS_RECONSTRUCTION_PANEL_AUDIO),
            language_manager=language_manager,
            status_bar=status_bar,
        )
        self._reconstruction_plot_panel: GUIReconstructionPlotPanel = GUIReconstructionPlotPanel(
            layout_graphs=layout.graphs,
            initial_collapsed=session_manager.is_card_collapsed(TAG_RECONSTRUCTIONS_RECONSTRUCTION_PANEL_PLOT),
            language_manager=language_manager,
            status_bar=status_bar,
        )
        self._reconstruction_audio_panel.set_collapse_handler(self._on_card_collapse_changed)
        self._reconstruction_plot_panel.set_collapse_handler(self._on_card_collapse_changed)
        self._reconstruction_player_logic.on_position_changed = self._reconstruction_plot_panel.set_playback_position
        self._reconstruction_panel_logic: ReconstructionPanelLogic = ReconstructionPanelLogic(
            session_manager,
            reconstruction_manager,
            export_service,
            tracker_backends,
        )
        self._reconstruction_instruments_panel: GUIReconstructionInstrumentsPanel = GUIReconstructionInstrumentsPanel(
            pitch_stepper_style=layout.pitch_stepper_style,
            copy_width=layout.copy_width,
            feature_colors=layout.feature_colors,
            layout_graphs=layout.graphs,
            language_manager=language_manager,
            status_bar=status_bar,
            initial_collapsed=session_manager.is_card_collapsed(TAG_RECONSTRUCTIONS_INSTRUMENTS_PANEL),
        )
        self._reconstruction_instruments_panel.set_collapse_handler(self._on_instruments_collapse_changed)
        self._reconstruction_instruments_logic: ReconstructionInstrumentsLogic = ReconstructionInstrumentsLogic(
            reconstruction_manager,
            scheduling=layout.scheduling,
        )

        self._browser_panel.on_refresh_tree = self._browser_logic.refresh_tree
        self._browser_panel.on_reconstruct_file = on_reconstruct_file
        self._browser_panel.on_reconstruct_directory = on_reconstruct_directory
        self._browser_panel.on_load_reconstruction = on_load_reconstruction_with_confirmation
        self._browser_panel.on_reconstruction_remove_requested = self._request_remove_reconstruction
        self._browser_panel.on_directory_remove_requested = self._request_remove_directory

        self._reconstruction_audio_panel.on_audio_source_changed = self._reconstruction_panel_logic.set_audio_source
        self._reconstruction_plot_panel.on_generators_changed = self._reconstruction_panel_logic.set_selected_generators
        self._browser_panel.on_locate_original_audio = self._original_audio_locator.locate

        self._reconstruction_panel_logic.on_view_changed = self._update_reconstruction_view
        self._reconstruction_panel_logic.on_audio_data_changed = self._on_audio_data_changed
        self._reconstruction_panel_logic.on_waveform_load_changed = self._reconstruction_plot_panel.load_waveform_data
        self._reconstruction_panel_logic.on_waveform_update_changed = (
            self._reconstruction_plot_panel.update_waveform_data
        )
        self._reconstruction_panel_logic.on_waveform_cleared = self._reconstruction_plot_panel.clear_waveform
        self._reconstruction_panel_logic.on_waveform_source_changed = (
            self._reconstruction_plot_panel.set_waveform_top_source
        )
        self._reconstruction_panel_logic.on_open_export_instrument_dialog = self._open_export_instrument_dialog
        self._reconstruction_panel_logic.on_open_export_instruments_dialog = self._open_export_instruments_dialog
        self._reconstruction_panel_logic.on_open_export_wav_dialog = self._open_export_wav_dialog
        self._reconstruction_panel_logic.on_locate_audio_not_found = lambda path: dialogs.show_file_not_found(
            path,
            language_manager["reconstructions.reconstruction.message.locate_audio_failed"],
        )

        export_service.subscribe(self._on_export_result)

        self._reconstruction_instruments_logic.on_view_changed = self._reconstruction_instruments_panel.update_view
        self._reconstruction_instruments_logic.on_feature_data_changed = (
            self._reconstruction_instruments_panel.update_feature_data
        )
        self._reconstruction_instruments_logic.on_reconstruction_instrument_updated = (
            on_reconstruction_instrument_updated
        )

        self._reconstruction_instruments_panel.on_instrument_export = (
            self._reconstruction_panel_logic.request_export_instrument_dialog
        )
        self._reconstruction_instruments_panel.on_reconstruction_instrument_hovered = (
            self._reconstruction_plot_panel.set_overlay
        )
        self._reconstruction_instruments_panel.on_pitch_value_changed = (
            self._reconstruction_instruments_logic.handle_pitch_value_changed
        )
        self._reconstruction_instruments_panel.on_bar_data_changed = (
            self._reconstruction_instruments_logic.handle_bar_point_clicked
        )
        self._reconstruction_instruments_panel.on_raw_data_changed = (
            self._reconstruction_instruments_logic.handle_raw_data_changed
        )

    def _on_export_result(self, result: ExportResult) -> None:
        messages = self._export_messages
        match result:
            case ExportSuccess(kind=ExportKind.WAV, filepath=fp):
                self._dialogs.show_message_with_path(messages.wav_title, messages.wav_success, fp)
            case ExportSuccess(
                kind=ExportKind.INSTRUMENT,
                filepath=fp,
                truncation=truncation,
            ):
                self._dialogs.show_message_with_path(
                    messages.status_title,
                    self._export_message(
                        messages.instrument_success,
                        messages.instrument_truncated,
                        truncation,
                    ),
                    fp,
                )
            case ExportSuccess(
                kind=ExportKind.SAMPLE,
                filepath=fp,
                truncation=truncation,
            ):
                self._dialogs.show_message_with_path(
                    messages.status_title,
                    self._export_message(
                        messages.instruments_success,
                        messages.instruments_truncated,
                        truncation,
                    ),
                    fp,
                )
            case ExportError(kind=ExportKind.WAV, exception=exception):
                self._dialogs.show_error(exception, messages.wav_failed)
            case ExportError(kind=ExportKind.INSTRUMENT, exception=exception):
                self._dialogs.show_error(exception, messages.instrument_failed)
            case ExportError(kind=ExportKind.SAMPLE, exception=exception):
                self._dialogs.show_error(exception, messages.instruments_failed)

    def _export_message(
        self,
        success: str,
        shortened: str,
        truncation: Optional[EnvelopeTruncation],
    ) -> str:
        """Follows the success line with the frames the FamiTracker sequence limit left out.

        Args:
            success: The message shown for a complete export.
            shortened: The template describing what a shortened export carries.
            truncation: The shortening the export underwent, or ``None`` when it fit whole.

        Returns:
            str: The message for the export result dialog.
        """
        if truncation is None:
            return success

        note = shortened.format(
            frames=truncation.frames,
            source_frames=truncation.source_frames,
            instruments=truncation.instruments,
        )
        return f"{success}\n\n{note}"

    def _update_reconstruction_view(
        self,
        view_model: ReconstructionViewModel,
    ) -> None:
        """Fans the reconstruction view model out to the audio and plot cards."""
        self._reconstruction_audio_panel.update_view(view_model)
        self._reconstruction_plot_panel.update_view(view_model)

    def _open_export_instrument_dialog(
        self,
        default_filename: str,
        default_path: str,
        generator_name: GeneratorName,
    ) -> None:
        """Prompts for the file the ``generator_name`` slice is written to.

        Every format that writes a single slice is offered at once, so the type picked in the
        dialog names the tracker the slice is written for.
        """
        filepath = save_file_dialog(
            title=self._language_manager["reconstructions.instruments.title.export_instrument_dialog"],
            initial_directory=default_path,
            default_filename=default_filename,
            filters=self._instrument_filters(),
        )
        self._handle_export_instrument(filepath, generator_name)

    def _instrument_filters(self) -> Tuple[FileFilter, ...]:
        """The types a destination for one slice may be given, one per tracker offered.

        Naming each tracker's own type puts the trackers an export can reach in the dialog's
        type selector, so the one that is picked there names the format.
        """
        return tuple(
            self._tracker_filter(tracker_format, ExportScope.INSTRUMENT) for tracker_format in INSTRUMENT_EXPORT_FORMATS
        )

    @ignore_none_path
    def _handle_export_instrument(
        self,
        filepath: Path,
        generator_name: GeneratorName,
    ) -> None:
        self._reconstruction_panel_logic.handle_export_instrument_confirmed(filepath, generator_name)

    def _open_export_instruments_dialog(
        self,
        default_filename: str,
        default_path: str,
        tracker_format: TrackerFormat,
    ) -> None:
        """Prompts for the destination the loaded reconstruction's slices are named after.

        The tracker was chosen with the action, so the dialog offers its file type alone: a
        format that gathers the whole reconstruction into one document writes it at the
        destination, while one that keeps an instrument per file writes its slices beside it.
        """
        destination = save_file_dialog(
            title=self._language_manager["reconstructions.instruments.title.export_instruments_dialog"],
            initial_directory=default_path,
            default_filename=default_filename,
            filters=(self._tracker_filter(tracker_format, ExportScope.SAMPLE),),
        )
        self._handle_export_instruments(destination, tracker_format)

    def _tracker_filter(
        self,
        tracker_format: TrackerFormat,
        scope: ExportScope,
    ) -> FileFilter:
        """The type ``tracker_format`` writes ``scope`` files as, named after that tracker."""
        return FileFilter.for_extensions(
            self._instrument_filter_names[tracker_format],
            [self._tracker_backends[tracker_format].extension(scope)],
        )

    @ignore_none_path
    def _handle_export_instruments(
        self,
        destination: Path,
        tracker_format: TrackerFormat,
    ) -> None:
        self._reconstruction_panel_logic.handle_export_instruments_confirmed(destination, tracker_format)

    def _open_export_wav_dialog(self, default_filename: str, default_path: str) -> None:
        filepath = save_file_dialog(
            title=self._export_messages.wav_title,
            initial_directory=default_path,
            default_filename=default_filename,
            filters=(FileFilter.for_extensions(self._language_manager["global.dialog.filter.wave"], [EXT_FILE_WAVE]),),
        )
        self._handle_export_wav(filepath)

    @ignore_none_path
    def _handle_export_wav(self, filepath: Path) -> None:
        self._reconstruction_panel_logic.handle_export_wav_confirmed(filepath)

    def create_tab(self) -> None:
        with dpg.tab(
            tag=TAG_GLOBAL_TAB_RECONSTRUCTION,
            parent=TAG_GLOBAL_TABS,
            label=self._language_manager["global.menu.label.tab_reconstruction"],
        ):
            self._side_panel_count = TabColumns.build(
                panel_gap=self._geometry.panel_gap,
                columns=[
                    ColumnSpec(
                        tag=_LEFT_COLUMN_TAG,
                        build=self._browser_panel.create_panel,
                        theme=TAG_GLOBAL_THEME_PANEL_SURFACE,
                        width=self._geometry.side_width,
                        height=self._geometry.side_height,
                        no_scrollbar=True,
                    ),
                    ColumnSpec(
                        tag=_CENTER_COLUMN_TAG,
                        build=self._build_reconstruction_column,
                        theme=TAG_GLOBAL_THEME_PANEL_GROUND,
                        border=False,
                    ),
                    ColumnSpec(
                        tag=_RIGHT_COLUMN_TAG,
                        build=self._reconstruction_instruments_panel.create_panel,
                        theme=TAG_GLOBAL_THEME_PANEL_GROUND,
                        width=self._instruments_width,
                        height=self._right_height,
                        no_scrollbar=True,
                        border=False,
                    ),
                ],
            )

        self._sync_browser_width()
        self._sync_instruments_width()

    def _build_reconstruction_column(self, parent: str) -> None:
        """Stacks the audio and plot cards down the centre column."""
        self._reconstruction_audio_panel.create_panel(parent)
        dpg.add_spacer(height=self._geometry.panel_gap, parent=parent)
        self._reconstruction_plot_panel.create_panel(parent)

    def _on_card_collapse_changed(
        self,
        card_tag: str,
        collapsed: bool,
    ) -> None:
        """Persists a card's collapsed state so it restores on the next launch."""
        self._session_manager.set_card_collapsed(card_tag, collapsed)

    def _on_browser_collapse_changed(
        self,
        card_tag: str,
        collapsed: bool,
    ) -> None:
        """Persists the browser panel's collapse, then docks or restores the width of the column it fills."""
        self._session_manager.set_card_collapsed(card_tag, collapsed)
        self._sync_browser_width()

    def _on_instruments_collapse_changed(
        self,
        card_tag: str,
        collapsed: bool,
    ) -> None:
        """Persists the instruments panel's collapse, then docks or restores the width of the column it fills."""
        self._session_manager.set_card_collapsed(card_tag, collapsed)
        self._sync_instruments_width()

    def sync_responsive_layout(self) -> None:
        """Refits both side columns to the current viewport, the entry the resize handler calls."""
        self._sync_browser_width()
        self._sync_instruments_width()

    def _sync_browser_width(self) -> None:
        """Shrinks the browser column to the collapse rail when collapsed, else sizes it to the viewport width."""
        if self._browser_panel.collapsed:
            width = self._geometry.rail_width
        else:
            width = expanded_side_width(
                self._geometry.side_width,
                dpg.get_viewport_client_width(),
                self._geometry.baseline_viewport_width,
                self._side_panel_count,
                self._geometry.center_weight,
            )

        dpg_configure_item(_LEFT_COLUMN_TAG, width=width)

    def _sync_instruments_width(self) -> None:
        """Shrinks the instruments column to the collapse rail when collapsed, else sizes it to the viewport width."""
        if self._reconstruction_instruments_panel.collapsed:
            width = self._geometry.rail_width
        else:
            width = expanded_side_width(
                self._instruments_width,
                dpg.get_viewport_client_width(),
                self._geometry.baseline_viewport_width,
                self._side_panel_count,
                self._geometry.center_weight,
            )

        dpg_configure_item(_RIGHT_COLUMN_TAG, width=width)

    def lock(self) -> None:
        self._browser_panel.lock()

    def unlock(self) -> None:
        self._browser_panel.unlock()

    def refresh_browser(self) -> None:
        self._browser_panel.refresh()

    def display_reconstruction(self) -> None:
        self._reconstruction_panel_logic.display_reconstruction()
        self._reconstruction_instruments_logic.update_display()

    def close_reconstruction(self) -> None:
        self._reconstruction_panel_logic.close_reconstruction()
        self._reconstruction_instruments_logic.update_display()

    def _request_remove_reconstruction(self, filepath: Path) -> None:
        self._dialogs.show_confirmation(
            tag=TAG_RECONSTRUCTIONS_BROWSER_DIALOG_REMOVE_RECONSTRUCTION_CONFIRMATION,
            title=self._language_manager["reconstructions.browser.title.remove_reconstruction_dialog"],
            message=self._language_manager["reconstructions.browser.message.remove_reconstruction_message"],
            on_confirm=lambda: self._remove_reconstruction(filepath),
            ok_label=self._lbl_remove,
            path=filepath,
        )

    def _request_remove_directory(self, directory: Path) -> None:
        self._dialogs.show_confirmation(
            tag=TAG_RECONSTRUCTIONS_BROWSER_DIALOG_REMOVE_DIRECTORY_CONFIRMATION,
            title=self._language_manager["reconstructions.browser.title.remove_directory_dialog"],
            message=self._language_manager["reconstructions.browser.message.remove_directory_message"],
            on_confirm=lambda: self._remove_directory(directory),
            ok_label=self._lbl_remove,
            path=directory,
        )

    def _remove_reconstruction(self, filepath: Path) -> None:
        if self._reconstruction_manager.filepath == filepath:
            self._reconstruction_manager.detach_current_reconstruction()
            self._reconstruction_manager.mark_updated()

        try:
            self._browser_logic.remove_path(filepath)
        except OSError as exception:
            logger.error_with_traceback(exception, f"Failed to remove reconstruction: {filepath}")
            self._dialogs.show_error(exception, self._msg_load_error)
            return

        self._browser_panel.refresh()

    def _remove_directory(self, directory: Path) -> None:
        current_filepath = self._reconstruction_manager.filepath
        if current_filepath is not None and current_filepath.is_relative_to(directory):
            self._reconstruction_manager.detach_current_reconstruction()
            self._reconstruction_manager.mark_updated()

        try:
            self._browser_logic.remove_path(directory)
        except OSError as exception:
            logger.error_with_traceback(
                exception,
                f"Failed to remove directory: {directory}",
            )
            self._dialogs.show_error(exception, self._msg_load_error)
            return

        self._browser_panel.refresh()

    def update_reconstruction(self) -> None:
        self._reconstruction_panel_logic.update_reconstruction()

    def set_reconstruction_dimmed(self, dimmed: bool) -> None:
        self._reconstruction_plot_panel.set_reconstruction_dimmed(dimmed)

    @property
    def player(self) -> AudioPlayerProtocol:
        return self._guarded_player

    def request_export_wav_dialog(self) -> None:
        self._reconstruction_panel_logic.request_export_wav_dialog()

    def request_export_instruments_dialog(self, tracker_format: TrackerFormat) -> None:
        self._reconstruction_panel_logic.request_export_instruments_dialog(tracker_format)

    def _on_browser_autoplay_error(self, exception: Exception) -> None:
        FrameCallbackManager.set_frame_callback(lambda: self._dialogs.show_error(exception))

    def _on_audio_data_changed(self, audio_data: Optional[AudioData]) -> None:
        if audio_data is None:
            self._reconstruction_player_logic.clear_audio()
        else:
            self._reconstruction_player_logic.load_audio_data(audio_data)

    def set_on_add_to_sequencer(self, callback: PathCallback) -> None:
        self._browser_panel.on_add_to_sequencer = callback

    def set_can_add_to_sequencer(self, predicate: Callable[[], bool]) -> None:
        self._browser_panel.can_add_to_sequencer = predicate

    def locate_original_audio(self) -> None:
        """Reveals the loaded reconstruction's original audio file in the OS file manager."""
        self._reconstruction_panel_logic.handle_locate_original_audio()

    def open_reconstruction_in_explorer(self) -> None:
        """Reveals the loaded reconstruction's own file in the OS file manager."""
        self._reconstruction_panel_logic.open_reconstruction_in_explorer()

    def load_reconstruction(self, filepath: Path) -> None:
        self._browser_panel.lock()
        try:
            self._reconstruction_manager.load_reconstruction(filepath)
            logger.info(f"Loaded reconstruction: {logger.format_path(filepath)}")
        except FileNotFoundError as exception:
            logger.error_with_traceback(
                exception,
                f"Failed to load reconstruction data from {filepath}",
            )
            self._dialogs.show_file_not_found(
                filepath,
                self._language_manager["reconstructions.browser.message.file_not_found"],
            )
        except (IsADirectoryError, PermissionError, OSError) as exception:
            logger.error_with_traceback(
                exception,
                f"Error while loading reconstruction data from {filepath}",
            )
            self._dialogs.show_error(exception, self._msg_load_error)
        except InvalidMetadataError as exception:
            logger.error_with_traceback(
                exception,
                f"Invalid metadata in the reconstruction file {filepath}",
            )
            self._dialogs.show_error(exception, self._language_manager["global.dialog.message.invalid_metadata_error"])
        except InvalidReconstructionValuesError as exception:
            logger.error_with_traceback(
                exception,
                f"Reconstruction contains invalid values: {filepath}",
            )
            self._dialogs.show_error(
                exception,
                self._language_manager["reconstructions.browser.message.invalid_values"],
            )
        except InvalidReconstructionError as exception:
            logger.error_with_traceback(
                exception,
                f"Invalid reconstruction file: {filepath}",
            )
            self._dialogs.show_error(exception, self._language_manager["reconstructions.browser.message.invalid_file"])
        except IncompatibleReconstructionVersionError as exception:
            logger.error_with_traceback(
                exception,
                f"Incompatible reconstruction version: {exception.actual_version}"
                f" != expected {exception.expected_version}",
            )
            self._dialogs.show_error(
                exception,
                self._language_manager["reconstructions.browser.template.incompatible_version_template"].format(
                    exception.actual_version,
                    exception.expected_version,
                ),
            )
        except DeserializationError as exception:
            logger.error_with_traceback(
                exception,
                f"Deserialization error while loading reconstruction from {filepath}",
            )
            self._dialogs.show_error(
                exception,
                self._language_manager["reconstructions.browser.message.deserialization_error"],
            )
        except LoadReconstructionError as exception:
            logger.error_with_traceback(
                exception,
                f"Unhandled load error while loading reconstruction data from {filepath}",
            )
            self._dialogs.show_error(exception, self._msg_load_error)
        finally:
            self._browser_panel.unlock()
