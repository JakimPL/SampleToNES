from pathlib import Path
from typing import Callable, Optional

import dearpygui.dearpygui as dpg

from sampletones_application.config.application.manager import ApplicationConfigManager
from sampletones_application.config.manager import ConfigManager
from sampletones_application.constants.general import (
    DIM_PANEL_HEIGHT_LEFT,
    DIM_PANEL_HEIGHT_RIGHT,
    DIM_PANEL_WIDTH_LEFT,
    DIM_PANEL_WIDTH_RECONSTRUCTIONS_DETAILS,
    LBL_TAB_RECONSTRUCTIONS,
    MSG_GLOBAL_INVALID_METADATA_ERROR,
    SUF_PANEL_CENTER,
    SUF_PANEL_LEFT,
    SUF_PANEL_RIGHT,
    TAG_TAB_RECONSTRUCTIONS,
    TAG_TABS,
)
from sampletones_application.constants.reconstructions import (
    MSG_RECONSTRUCTIONS_BROWSER_DESERIALIZATION_ERROR,
    MSG_RECONSTRUCTIONS_BROWSER_FILE_LOAD_ERROR,
    MSG_RECONSTRUCTIONS_BROWSER_INVALID_RECONSTRUCTION_FILE,
    MSG_RECONSTRUCTIONS_BROWSER_INVALID_RECONSTRUCTION_VALUES,
    MSG_RECONSTRUCTIONS_BROWSER_RECONSTRUCTION_FILE_NOT_FOUND,
    MSG_RECONSTRUCTIONS_RECONSTRUCTION_AUDIO_MISSING,
    MSG_RECONSTRUCTIONS_RECONSTRUCTION_EXPORT_FTI_FAILED,
    MSG_RECONSTRUCTIONS_RECONSTRUCTION_EXPORT_FTI_SUCCESS,
    MSG_RECONSTRUCTIONS_RECONSTRUCTION_EXPORT_FTIS_FAILED,
    MSG_RECONSTRUCTIONS_RECONSTRUCTION_EXPORT_FTIS_SUCCESS,
    MSG_RECONSTRUCTIONS_RECONSTRUCTION_EXPORT_WAV_FAILED,
    MSG_RECONSTRUCTIONS_RECONSTRUCTION_EXPORT_WAV_SUCCESS,
    MSG_RECONSTRUCTIONS_RECONSTRUCTION_LOCATE_AUDIO_FAILED,
    TAG_DIALOG_RECONSTRUCTIONS_RECONSTRUCTION_AUDIO_MISSING,
    TPL_RECONSTRUCTIONS_BROWSER_INCOMPATIBLE_RECONSTRUCTION_FILE,
    TTL_DIALOG_EXPORT_WAV,
    TTL_DIALOG_RECONSTRUCTIONS_RECONSTRUCTION_AUDIO_MISSING,
    TTL_DIALOG_RECONSTRUCTIONS_RECONSTRUCTION_EXPORT_STATUS,
)
from sampletones_application.logic.player.player import PlayerLogic
from sampletones_application.logic.reconstruction.browser import BrowserLogic
from sampletones_application.logic.reconstruction.browser_manager import BrowserManager
from sampletones_application.logic.reconstruction.details import (
    OnReconstructionInstrumentUpdatedCallback,
    ReconstructionDetailsLogic,
)
from sampletones_application.logic.reconstruction.manager import ReconstructionManager
from sampletones_application.logic.reconstruction.reconstruction import ReconstructionPanelLogic
from sampletones_application.ui.panels.reconstruction.browser.browser import GUIBrowserPanel
from sampletones_application.ui.panels.reconstruction.details.details import GUIReconstructionDetailsPanel
from sampletones_application.ui.panels.reconstruction.reconstruction.reconstruction import GUIReconstructionPanel
from sampletones_application.utils.dialogs import (
    show_error_dialog,
    show_file_not_found_dialog,
    show_info_dialog,
    show_message_with_path_dialog,
)
from sampletones_application.utils.shortcuts.manager import ShortcutManager
from sampletones_core.audio import AudioDeviceManager
from sampletones_shared.exceptions import (
    DeserializationError,
    IncompatibleReconstructionVersionError,
    InvalidMetadataError,
    InvalidReconstructionError,
    InvalidReconstructionValuesError,
)
from sampletones_shared.logger import logger
from sampletones_shared.types.callback import VoidCallback


class ReconstructionsTabCoordinator:
    def __init__(
        self,
        config_manager: ConfigManager,
        application_config_manager: ApplicationConfigManager,
        audio_device_manager: AudioDeviceManager,
        shortcut_manager: ShortcutManager,
        reconstruction_manager: ReconstructionManager,
        browser_manager: BrowserManager,
        on_load_reconstruction_with_confirmation: Callable[[Optional[Path]], None],
        on_reconstruction_loaded: VoidCallback,
        on_reconstruct_file: VoidCallback,
        on_reconstruct_directory: VoidCallback,
        on_change_audio_state: VoidCallback,
        on_reconstruction_instrument_updated: OnReconstructionInstrumentUpdatedCallback,
    ) -> None:
        self._reconstruction_manager = reconstruction_manager

        self._browser_logic: BrowserLogic = BrowserLogic(config_manager, browser_manager)
        self._browser_panel: GUIBrowserPanel = GUIBrowserPanel(
            self._browser_logic,
            application_config_manager,
            audio_device_manager,
            shortcut_manager,
        )
        self._reconstruction_player_logic = PlayerLogic(audio_device_manager, on_change_audio_state)
        self._reconstruction_panel: GUIReconstructionPanel = GUIReconstructionPanel(
            self._reconstruction_player_logic,
        )
        self._reconstruction_panel_logic: ReconstructionPanelLogic = ReconstructionPanelLogic(
            application_config_manager,
            reconstruction_manager,
        )
        self._reconstruction_details_panel: GUIReconstructionDetailsPanel = GUIReconstructionDetailsPanel(
            shortcut_manager,
        )
        self._reconstruction_details_logic: ReconstructionDetailsLogic = ReconstructionDetailsLogic(
            reconstruction_manager,
        )

        self._browser_logic.set_callbacks(
            load_reconstruction_with_confirmation=on_load_reconstruction_with_confirmation,
            on_reconstruction_loaded=on_reconstruction_loaded,
            on_reconstruct_file=on_reconstruct_file,
            on_reconstruct_directory=on_reconstruct_directory,
        )

        self._reconstruction_panel.on_audio_source_changed = self._reconstruction_panel_logic.set_audio_source
        self._reconstruction_panel.on_generators_changed = self._reconstruction_panel_logic.set_selected_generators
        self._reconstruction_panel.on_export_wav_requested = self.request_export_wav_dialog
        self._reconstruction_panel.on_export_instrument_confirmed = (
            self._reconstruction_panel_logic.handle_export_instrument_confirmed
        )
        self._reconstruction_panel.on_export_instruments_confirmed = (
            self._reconstruction_panel_logic.handle_export_instruments_confirmed
        )
        self._reconstruction_panel.on_export_wav_confirmed = (
            self._reconstruction_panel_logic.handle_export_wav_confirmed
        )
        self._reconstruction_panel.on_locate_original_audio_requested = (
            self._reconstruction_panel_logic.handle_locate_original_audio
        )

        self._reconstruction_panel_logic.on_view_changed = self._reconstruction_panel.update_view
        self._reconstruction_panel_logic.on_audio_data_changed = self._reconstruction_panel.update_audio_data
        self._reconstruction_panel_logic.on_waveform_load_changed = self._reconstruction_panel.load_waveform_data
        self._reconstruction_panel_logic.on_waveform_update_changed = self._reconstruction_panel.update_waveform_data
        self._reconstruction_panel_logic.on_waveform_cleared = self._reconstruction_panel.clear_waveform
        self._reconstruction_panel_logic.on_open_export_instrument_dialog = (
            self._reconstruction_panel.open_export_instrument_dialog
        )
        self._reconstruction_panel_logic.on_open_export_instruments_dialog = (
            self._reconstruction_panel.open_export_instruments_dialog
        )
        self._reconstruction_panel_logic.on_open_export_wav_dialog = self._reconstruction_panel.open_export_wav_dialog
        self._reconstruction_panel_logic.on_export_instrument_success = lambda filepath: show_message_with_path_dialog(
            TTL_DIALOG_RECONSTRUCTIONS_RECONSTRUCTION_EXPORT_STATUS,
            MSG_RECONSTRUCTIONS_RECONSTRUCTION_EXPORT_FTI_SUCCESS,
            filepath,
        )
        self._reconstruction_panel_logic.on_export_instrument_error = lambda exception: show_error_dialog(
            exception, MSG_RECONSTRUCTIONS_RECONSTRUCTION_EXPORT_FTI_FAILED
        )
        self._reconstruction_panel_logic.on_export_instruments_success = lambda filepath: show_message_with_path_dialog(
            TTL_DIALOG_RECONSTRUCTIONS_RECONSTRUCTION_EXPORT_STATUS,
            MSG_RECONSTRUCTIONS_RECONSTRUCTION_EXPORT_FTIS_SUCCESS,
            filepath,
        )
        self._reconstruction_panel_logic.on_export_instruments_error = lambda exception: show_error_dialog(
            exception, MSG_RECONSTRUCTIONS_RECONSTRUCTION_EXPORT_FTIS_FAILED
        )
        self._reconstruction_panel_logic.on_export_wav_success = lambda filepath: show_message_with_path_dialog(
            TTL_DIALOG_EXPORT_WAV,
            MSG_RECONSTRUCTIONS_RECONSTRUCTION_EXPORT_WAV_SUCCESS,
            filepath,
        )
        self._reconstruction_panel_logic.on_export_wav_error = lambda exception: show_error_dialog(
            exception, MSG_RECONSTRUCTIONS_RECONSTRUCTION_EXPORT_WAV_FAILED
        )
        self._reconstruction_panel_logic.on_locate_audio_missing = lambda: show_info_dialog(
            TAG_DIALOG_RECONSTRUCTIONS_RECONSTRUCTION_AUDIO_MISSING,
            MSG_RECONSTRUCTIONS_RECONSTRUCTION_AUDIO_MISSING,
            TTL_DIALOG_RECONSTRUCTIONS_RECONSTRUCTION_AUDIO_MISSING,
        )
        self._reconstruction_panel_logic.on_locate_audio_not_found = lambda path: show_file_not_found_dialog(
            path, MSG_RECONSTRUCTIONS_RECONSTRUCTION_LOCATE_AUDIO_FAILED
        )

        self._reconstruction_details_logic.on_view_changed = self._reconstruction_details_panel.update_view
        self._reconstruction_details_logic.on_feature_data_changed = (
            self._reconstruction_details_panel.update_feature_data
        )
        self._reconstruction_details_logic.on_pitch_changed = self._reconstruction_details_panel.update_pitch
        self._reconstruction_details_logic.on_reconstruction_instrument_updated = on_reconstruction_instrument_updated

        self._reconstruction_details_panel.on_instrument_export = (
            self._reconstruction_panel_logic.request_export_instrument_dialog
        )
        self._reconstruction_details_panel.on_instruments_export = (
            self._reconstruction_panel_logic.request_export_instruments_dialog
        )
        self._reconstruction_details_panel.on_reconstruction_instrument_hovered = self._reconstruction_panel.set_overlay
        self._reconstruction_details_panel.on_pitch_input = self._reconstruction_details_logic.handle_pitch_input
        self._reconstruction_details_panel.on_pitch_step = self._reconstruction_details_logic.handle_pitch_step
        self._reconstruction_details_panel.on_hold_tick = self._reconstruction_details_logic.handle_hold_tick
        self._reconstruction_details_panel.on_hold_ended = self._reconstruction_details_logic.handle_hold_ended
        self._reconstruction_details_panel.on_bar_data_changed = (
            self._reconstruction_details_logic.handle_bar_point_clicked
        )
        self._reconstruction_details_panel.on_raw_data_changed = (
            self._reconstruction_details_logic.handle_raw_data_changed
        )

    def create_tab(self) -> None:
        with dpg.tab(
            tag=TAG_TAB_RECONSTRUCTIONS,
            parent=TAG_TABS,
            label=LBL_TAB_RECONSTRUCTIONS,
        ):
            with dpg.table(
                parent=TAG_TAB_RECONSTRUCTIONS,
                header_row=False,
                resizable=False,
                policy=dpg.mvTable_SizingStretchProp,
            ):
                dpg.add_table_column(width_fixed=True)
                dpg.add_table_column()
                dpg.add_table_column(width_fixed=True)

                with dpg.table_row():
                    with dpg.child_window(
                        tag=f"{TAG_TAB_RECONSTRUCTIONS}{SUF_PANEL_LEFT}",
                        width=DIM_PANEL_WIDTH_LEFT,
                        height=DIM_PANEL_HEIGHT_LEFT,
                        no_scrollbar=True,
                        no_scroll_with_mouse=True,
                    ):
                        self._browser_panel.create_panel()

                    with dpg.child_window(
                        tag=f"{TAG_TAB_RECONSTRUCTIONS}{SUF_PANEL_CENTER}",
                        no_scroll_with_mouse=True,
                    ):
                        self._reconstruction_panel.create_panel()

                    with dpg.child_window(
                        tag=f"{TAG_TAB_RECONSTRUCTIONS}{SUF_PANEL_RIGHT}",
                        width=DIM_PANEL_WIDTH_RECONSTRUCTIONS_DETAILS,
                        height=DIM_PANEL_HEIGHT_RIGHT,
                        no_scrollbar=True,
                        no_scroll_with_mouse=True,
                    ):
                        self._reconstruction_details_panel.create_panel()

    def lock(self) -> None:
        self._browser_panel.lock()

    def unlock(self) -> None:
        self._browser_panel.unlock()

    def refresh_browser(self) -> None:
        self._browser_panel.refresh()

    def display_reconstruction(self) -> None:
        self._reconstruction_panel_logic.display_reconstruction()
        self._reconstruction_details_logic.update_display()

    def close_reconstruction(self) -> None:
        self._reconstruction_panel_logic.close_reconstruction()
        self._reconstruction_details_logic.update_display()

    def update_reconstruction(self) -> None:
        self._reconstruction_panel_logic.update_reconstruction()

    @property
    def player_panel(self) -> GUIReconstructionPanel:
        return self._reconstruction_panel

    def request_export_wav_dialog(self) -> None:
        self._reconstruction_panel_logic.request_export_wav_dialog()

    def request_export_instruments_dialog(self) -> None:
        self._reconstruction_panel_logic.request_export_instruments_dialog()

    def load_reconstruction(self, filepath: Path) -> None:
        self._browser_panel.lock()
        try:
            self._reconstruction_manager.load_reconstruction(filepath)
            logger.info(f"Loaded reconstruction: {logger.format_path(filepath)}")
        except FileNotFoundError as exception:
            logger.error_with_traceback(exception, f"Failed to load reconstruction data from {filepath}")
            show_file_not_found_dialog(filepath, MSG_RECONSTRUCTIONS_BROWSER_RECONSTRUCTION_FILE_NOT_FOUND)
        except (IOError, IsADirectoryError, PermissionError, OSError) as exception:
            logger.error_with_traceback(exception, f"Error while loading reconstruction data from {filepath}")
            show_error_dialog(exception, MSG_RECONSTRUCTIONS_BROWSER_FILE_LOAD_ERROR)
        except InvalidMetadataError as exception:
            logger.error_with_traceback(exception, f"Invalid metadata in the reconstruction file {filepath}")
            show_error_dialog(exception, MSG_GLOBAL_INVALID_METADATA_ERROR)
        except InvalidReconstructionValuesError as exception:
            logger.error_with_traceback(exception, f"Reconstruction contains invalid values: {filepath}")
            show_error_dialog(exception, MSG_RECONSTRUCTIONS_BROWSER_INVALID_RECONSTRUCTION_VALUES)
        except InvalidReconstructionError as exception:
            logger.error_with_traceback(exception, f"Invalid reconstruction file: {filepath}")
            show_error_dialog(exception, MSG_RECONSTRUCTIONS_BROWSER_INVALID_RECONSTRUCTION_FILE)
        except IncompatibleReconstructionVersionError as exception:
            logger.error_with_traceback(
                exception,
                f"Incompatible reconstruction version: {exception.actual_version}"
                f" != expected {exception.expected_version}",
            )
            show_error_dialog(
                exception,
                TPL_RECONSTRUCTIONS_BROWSER_INCOMPATIBLE_RECONSTRUCTION_FILE.format(
                    exception.actual_version,
                    exception.expected_version,
                ),
            )
        except DeserializationError as exception:
            logger.error_with_traceback(
                exception, f"Deserialization error while loading reconstruction from {filepath}"
            )
            show_error_dialog(exception, MSG_RECONSTRUCTIONS_BROWSER_DESERIALIZATION_ERROR)
        except Exception as exception:  # TODO: narrow
            logger.error_with_traceback(
                exception, f"Unexpected error while loading reconstruction data from {filepath}"
            )
            show_error_dialog(exception, MSG_RECONSTRUCTIONS_BROWSER_FILE_LOAD_ERROR)
        finally:
            self._browser_panel.unlock()
