from pathlib import Path
from typing import Optional

import dearpygui.dearpygui as dpg

from sampletones_application.categories.manager import LanguageManager
from sampletones_application.config.managers.config import ConfigManager
from sampletones_application.config.managers.session import SessionManager
from sampletones_application.constants.conversion import MAX_STEM_SOURCES
from sampletones_application.constants.output import OutputKind
from sampletones_application.coordinators.tabs.hooks import MainTabHooks
from sampletones_application.logic.instruction.library_manager import (
    InstructionsLibraryManager,
)
from sampletones_application.logic.main.converter.logic import ConverterLogic
from sampletones_application.logic.main.converter.run import ConversionSuccess
from sampletones_application.logic.main.explorer_manager import ExplorerManager
from sampletones_application.logic.shared.tree import TreeLogic
from sampletones_application.parameters.main import MainTabParameters
from sampletones_application.services.conversion.service import ConversionService
from sampletones_application.tags.compose import compose_tag
from sampletones_application.tags.general import (
    SUF_PANEL_CENTER,
    SUF_PANEL_LEFT,
    TAG_GLOBAL_TAB_MAIN,
    TAG_GLOBAL_TABS,
    TAG_GLOBAL_THEME_PANEL_GROUND,
    TAG_GLOBAL_THEME_PANEL_SURFACE,
)
from sampletones_application.tags.main import (
    TAG_MAIN_ADVANCED_PANEL,
    TAG_MAIN_CONFIG_PANEL,
    TAG_MAIN_CONFIG_PANEL_CONFIG_CELL,
    TAG_MAIN_CONFIG_TABLE_CONFIG_ROW,
    TAG_MAIN_CONVERTER_DIALOG_CANCEL,
    TAG_MAIN_CONVERTER_DIALOG_DISCARD_STEMS,
    TAG_MAIN_CONVERTER_DIALOG_LOAD,
    TAG_MAIN_CONVERTER_DIALOG_OVERWRITE_TARGET,
    TAG_MAIN_CONVERTER_PANEL,
    TAG_MAIN_EXPLORER_DIALOG_CONVERTER_RUNNING,
    TAG_MAIN_EXPLORER_PANEL,
    TAG_MAIN_RECONSTRUCTOR_PANEL,
    TAG_MAIN_RECONSTRUCTOR_PANEL_RECONSTRUCTOR_CELL,
)
from sampletones_application.ui.elements.layout.columns import ColumnSpec, TabColumns
from sampletones_application.ui.elements.layout.responsive import expanded_side_width
from sampletones_application.ui.elements.status import GUIStatusBar
from sampletones_application.ui.panels.dialogs.stem_selection import GUIStemSelectionWindow
from sampletones_application.ui.panels.main.advanced import GUIAdvancedSettingsPanel
from sampletones_application.ui.panels.main.config import GUIConfigPanel
from sampletones_application.ui.panels.main.converter import GUIConverterPanel
from sampletones_application.ui.panels.main.explorer import GUIExplorerPanel
from sampletones_application.ui.panels.main.reconstructor import GUIReconstructorPanel
from sampletones_application.utils.file_dialogs.api import select_directory_dialog
from sampletones_application.utils.file_dialogs.result import ignore_none_path
from sampletones_application.utils.gui.dialogs import DialogsRenderer
from sampletones_application.utils.gui.dpg import dpg_configure_item
from sampletones_application.utils.gui.frame import FrameCallbackManager
from sampletones_application.utils.gui.render_thread import on_render_thread
from sampletones_application.view_model.main.advanced import (
    AdvancedSettingsPanelViewModel,
)
from sampletones_application.view_model.main.config import ConfigPanelViewModel
from sampletones_application.view_model.main.converter import ConverterViewModel
from sampletones_application.view_model.main.reconstructor import (
    ReconstructorPanelViewModel,
)
from sampletones_core.audio import AudioDeviceManager
from sampletones_core.constants.enums import ChannelName
from sampletones_core.structures.tree import FileSystemNode
from sampletones_shared.logger import logger
from sampletones_shared.types.callback import VoidCallback

_LEFT_COLUMN_TAG = compose_tag(TAG_GLOBAL_TAB_MAIN, SUF_PANEL_LEFT)
_CENTER_COLUMN_TAG = compose_tag(TAG_GLOBAL_TAB_MAIN, SUF_PANEL_CENTER)


class MainTabCoordinator:
    """
    The owner of all components that make up the Main tab.

    The Main tab is the application's entry point for converting audio files
    into reconstructions.

    - Intra-tab callback topology is established entirely in the constructor;
      after that the tab operates autonomously.
    - The public API is intent-level — callers express what they want,
      not which component handles it.
    """

    def __init__(
        self,
        config_manager: ConfigManager,
        session_manager: SessionManager,
        audio_device_manager: AudioDeviceManager,
        library_manager: InstructionsLibraryManager,
        conversion_service: ConversionService,
        hooks: MainTabHooks,
        *,
        layout: MainTabParameters,
        language_manager: LanguageManager,
        dialogs: DialogsRenderer,
        status_bar: GUIStatusBar,
        stem_selection_window: GUIStemSelectionWindow,
    ) -> None:
        self._language_manager = language_manager
        self._config_manager = config_manager
        self._session_manager = session_manager
        self._library_manager = library_manager
        self._hooks = hooks
        self._dialogs = dialogs
        self._stem_selection_window = stem_selection_window

        self._geometry = layout.geometry
        self._side_panel_count: int
        self._config_height = layout.config_height
        self._ttl_progress = language_manager["main.converter.title.progress_dialog"]
        self._repaint_priority = layout.scheduling.priorities.gui_action

        self._build_explorer(
            config_manager,
            session_manager,
            audio_device_manager,
            layout=layout,
            language_manager=language_manager,
            status_bar=status_bar,
        )
        self._build_cards(
            config_manager,
            session_manager,
            conversion_service,
            layout=layout,
            language_manager=language_manager,
            status_bar=status_bar,
        )
        self._wire_settings(config_manager)
        self._wire_explorer()
        self._wire_converter(
            config_manager,
            library_manager,
            conversion_service,
            dialogs,
            language_manager,
        )

    def _build_explorer(
        self,
        config_manager: ConfigManager,
        session_manager: SessionManager,
        audio_device_manager: AudioDeviceManager,
        *,
        layout: MainTabParameters,
        language_manager: LanguageManager,
        status_bar: GUIStatusBar,
    ) -> None:
        """The file browser: what reads the disk, what plays from it, and what draws both."""
        self._explorer_logic: ExplorerManager = ExplorerManager(
            config_manager,
            language_manager=language_manager,
            open_directories=session_manager.expanded_directories,
        )
        self._explorer_tree_logic: TreeLogic = TreeLogic(
            session_manager,
            audio_device_manager,
            scheduling=layout.scheduling,
        )
        self._explorer_panel: GUIExplorerPanel = GUIExplorerPanel(
            self._explorer_logic,
            self._explorer_tree_logic,
            scheduling=layout.scheduling,
            language_manager=language_manager,
            status_bar=status_bar,
            colors=layout.tree_colors,
            initial_collapsed=session_manager.is_card_collapsed(TAG_MAIN_EXPLORER_PANEL),
        )
        self._explorer_tree_logic.on_lock_state_changed = self._explorer_panel.set_tree_enabled
        self._explorer_tree_logic.on_favorite_changed = self._repaint_explorer_favorites
        self._explorer_tree_logic.on_search_update_needed = self._explorer_panel.update_tree_visibility
        self._explorer_tree_logic.on_autoplay_error = self._on_explorer_autoplay_error

    def _build_cards(
        self,
        config_manager: ConfigManager,
        session_manager: SessionManager,
        conversion_service: ConversionService,
        *,
        layout: MainTabParameters,
        language_manager: LanguageManager,
        status_bar: GUIStatusBar,
    ) -> None:
        """The tab's cards and the converter behind them, each opening on what it last stood at."""
        _config = config_manager.config
        self._config_panel: GUIConfigPanel = GUIConfigPanel(
            ConfigPanelViewModel(
                normalize=_config.general.normalize,
                quantize=_config.general.quantize,
                sample_rate=_config.library.sample_rate,
                nes_frequency=_config.library.nes_frequency,
            ),
            layout=layout.main.config,
            inputs=layout.inputs,
            initial_collapsed=session_manager.is_card_collapsed(TAG_MAIN_CONFIG_PANEL),
            language_manager=language_manager,
            status_bar=status_bar,
        )
        self._converter_logic: ConverterLogic = ConverterLogic(
            config_manager,
            session_manager,
            conversion_service,
            scheduling=layout.scheduling,
            language_manager=language_manager,
            is_operation_active=self._hooks.is_operation_active,
        )
        self._reconstructor_panel: GUIReconstructorPanel = GUIReconstructorPanel(
            ReconstructorPanelViewModel(
                slots=self._converter_logic.settings_slots,
                inspected=None,
                drive=_config.generation.drive,
            ),
            layout=layout.main.reconstructor,
            inputs=layout.inputs,
            initial_collapsed=session_manager.is_card_collapsed(TAG_MAIN_RECONSTRUCTOR_PANEL),
            language_manager=language_manager,
            status_bar=status_bar,
        )
        self._advanced_settings_panel: GUIAdvancedSettingsPanel = GUIAdvancedSettingsPanel(
            AdvancedSettingsPanelViewModel(
                max_workers=_config.general.max_workers,
                spectrum_method=_config.library.spectrum_method,
                transformation_gamma=_config.library.transformation_gamma,
                library_directory=config_manager.get_library_directory(),
                reconstructions_directory=config_manager.get_reconstructions_directory(),
            ),
            layout=layout.main.advanced,
            inputs=layout.inputs,
            initial_collapsed=session_manager.is_card_collapsed(TAG_MAIN_ADVANCED_PANEL),
            language_manager=language_manager,
            status_bar=status_bar,
            path_colors=layout.path_colors,
        )
        self._converter_panel: GUIConverterPanel = GUIConverterPanel(
            layout=layout.main.converter,
            stems_layout=layout.stems,
            inputs=layout.inputs,
            path_colors=layout.path_colors,
            initial_collapsed=session_manager.is_card_collapsed(TAG_MAIN_CONVERTER_PANEL),
            language_manager=language_manager,
            status_bar=status_bar,
        )

    def _wire_settings(self, config_manager: ConfigManager) -> None:
        """What the settings cards report, and what redraws them when the configuration moves."""
        config_manager.add_config_change_callback(self._update_config_panel_view)
        config_manager.add_config_change_callback(self._update_reconstructor_panel_view)
        config_manager.add_config_change_callback(self._update_advanced_settings_panel_view)

        self._config_panel.on_audio_settings_changed = config_manager.apply_audio_settings
        self._config_panel.on_library_settings_changed = config_manager.apply_library_settings
        self._reconstructor_panel.on_generation_settings_changed = config_manager.apply_generation_settings
        self._reconstructor_panel.on_slot_toggled = self._converter_logic.toggle_slot
        self._advanced_settings_panel.on_advanced_settings_changed = config_manager.apply_advanced_settings
        self._advanced_settings_panel.on_select_library_directory = self._select_library_directory
        self._advanced_settings_panel.on_select_output_directory = self._select_output_directory

        self._wire_collapse_handlers()

    def _wire_explorer(self) -> None:
        """What a gesture in the browser reaches: the converter, the tab's own guards, the app."""
        self._explorer_panel.set_callbacks(
            on_wave_file_clicked=self._on_wave_file_clicked,
            on_directory_clicked=self._on_directory_clicked,
            on_directory_add_requested=self._on_directory_add_requested,
            on_file_add_requested=self._on_file_add_requested,
            can_add_stems=self._can_add_stems,
            on_reconstruct_file=self._request_reconstruct_file,
            on_reconstruct_directory=self._request_reconstruct_directory,
            on_load_reconstruction=self._hooks.on_load_reconstruction,
            on_load_library=self._hooks.on_load_library,
            on_set_as_library_directory=self._handle_select_library_directory,
            on_set_as_reconstructions_directory=self._advanced_settings_panel.change_reconstructions_directory,
        )

    def _wire_converter(
        self,
        config_manager: ConfigManager,
        library_manager: InstructionsLibraryManager,
        conversion_service: ConversionService,
        dialogs: DialogsRenderer,
        language_manager: LanguageManager,
    ) -> None:
        """What the converter reports and what answers it: the panel, the dialogs, the library."""
        _msg_converter_error = language_manager["main.converter.message.status_error"]
        _msg_no_files = language_manager["main.converter.message.status_no_files"]
        _msg_no_generators = language_manager["main.converter.message.status_no_channels"]
        self._converter_logic.on_view_changed = self._on_converter_view_changed
        self._converter_logic.on_success = self._on_conversion_success
        self._converter_logic.on_error = lambda error: dialogs.show_error(error, _msg_converter_error)
        self._converter_logic.on_no_files_to_process = lambda: dialogs.show_info(
            self._converter_panel.tag,
            _msg_no_files,
            self._ttl_progress,
        )
        self._converter_logic.on_no_generators = lambda: dialogs.show_info(
            self._converter_panel.tag,
            _msg_no_generators,
            self._ttl_progress,
        )
        self._converter_logic.on_target_exists = self._confirm_overwriting_target
        self._converter_logic.is_library_available = library_manager.is_library_available_for_config
        self._converter_logic.cancel_library_generation = library_manager.cancel_generation
        self._converter_logic.on_load_file = self._hooks.on_load_file
        self._converter_logic.on_load_directory = self._hooks.on_load_directory
        self._converter_logic.on_canceled = self._hooks.on_canceled
        self._converter_logic.generate_library = self._hooks.on_generate_library
        config_manager.add_config_change_callback(self._converter_logic.refresh_view)
        library_manager.on_generation_progress_extra = conversion_service.forward_library_progress

        self._converter_panel.on_convert_requested = self._converter_logic.start_conversion
        self._converter_panel.on_cancel_requested = self._request_cancel_confirmation
        self._converter_panel.on_output_changed = self._request_output
        self._converter_panel.on_channel_cap_changed = self._converter_logic.set_channel_cap
        self._converter_panel.on_hierarchy_mode_changed = self._converter_logic.set_hierarchy_mode
        self._converter_panel.on_source_channels_changed = self._converter_logic.set_source_channels
        self._converter_panel.on_source_removed = self._converter_logic.remove_source
        self._converter_panel.on_source_moved = self._converter_logic.move_source_within_level
        self._converter_panel.on_source_level_joined = self._converter_logic.join_source_level
        self._converter_panel.on_source_isolated = self._converter_logic.isolate_source
        self._converter_panel.on_source_dropped_on_source = self._converter_logic.move_source_onto
        self._converter_panel.on_source_dropped_on_level = self._converter_logic.move_source_to_new_level
        self._converter_panel.on_folder_removed = self._converter_logic.remove_folder
        self._converter_panel.on_folder_channel_toggled = self._converter_logic.toggle_folder_channel
        self._converter_panel.on_row_selected = self._converter_logic.select_row
        self._stem_selection_window.on_add = self._converter_logic.mix_only

    def _repaint_explorer_favorites(self, node: FileSystemNode) -> None:
        """Repaints the row whose star was toggled: the explorer mirrors the disk, so a path is one row."""
        self._explorer_panel.update_favorite_indicators((node,))

    def _on_explorer_autoplay_error(self, exception: Exception) -> None:
        FrameCallbackManager.set_frame_callback(lambda: self._dialogs.show_error(exception))

    def _on_converter_view_changed(self, view_model: ConverterViewModel) -> None:
        """The converter's own view, and the settings card that follows what it has picked out.

        A gesture on the list rebuilds the list, and DearPyGui calls a widget's callback on a
        thread of its own, so the redraw crosses to the render thread rather than tearing widgets
        down underneath the frame being walked.
        """
        on_render_thread(self._repaint_converter, view_model, priority=self._repaint_priority)

    def _repaint_converter(self, view_model: ConverterViewModel) -> None:
        self._converter_panel.update_view(view_model)
        self._update_reconstructor_panel_view()
        self._hooks.on_busy_state_changed()

    def _on_wave_file_clicked(self, filepath: Path) -> None:
        if not self._hooks.is_operation_active():
            self._converter_logic.gather_recordings([filepath])

    def _on_directory_clicked(self, directory_path: Path) -> None:
        if not self._hooks.is_operation_active():
            self._converter_logic.gather_folder(directory_path)

    def _request_reconstruct_file(self, filepath: Path) -> None:
        if self._notify_converter_running():
            return

        self._replacing_the_setup(lambda: self._hooks.on_reconstruct_file(filepath))

    def _request_reconstruct_directory(self, directory_path: Path) -> None:
        if self._notify_converter_running():
            return

        self._replacing_the_setup(lambda: self._hooks.on_reconstruct_directory(directory_path))

    def _replacing_the_setup(self, reconstruct: VoidCallback) -> None:
        """Runs a conversion the browser asked for, asking first where it would drop what was gathered.

        A Reconstruct names one file or one folder and converts that alone, so a setup already
        holding sources is what the reader is being asked about. Declining leaves the setup as it
        stands and starts nothing.
        """
        if not self._converter_logic.gathered_paths:
            reconstruct()
            return

        self._confirm_discarding_stems(reconstruct)

    def _confirm_discarding_stems(self, on_confirm: VoidCallback) -> None:
        self._dialogs.show_confirmation(
            TAG_MAIN_CONVERTER_DIALOG_DISCARD_STEMS,
            self._language_manager["main.converter.message.discard_stems_prompt"],
            self._language_manager["main.converter.title.discard_stems_dialog"],
            on_confirm,
            ok_label=self._language_manager["main.converter.label.discard_stems_button"],
            cancel_label=self._language_manager["main.converter.label.keep_stems_button"],
            on_cancel=self._converter_logic.refresh_view,
        )

    def _confirm_overwriting_target(self, target: Path) -> None:
        """Asks before a conversion writes over the reconstruction already standing at its target.

        A batch keeps what it finds and converts the rest, so this reaches the reader for a
        single conversion — the one run whose output would replace a file already made.
        """
        self._dialogs.show_confirmation(
            TAG_MAIN_CONVERTER_DIALOG_OVERWRITE_TARGET,
            self._language_manager["main.converter.message.overwrite_target_prompt"],
            self._language_manager["main.converter.title.overwrite_target_dialog"],
            lambda: self._converter_logic.start_conversion(confirmed=True),
            ok_label=self._language_manager["main.converter.label.overwrite_target_button"],
            path=target,
        )

    def _notify_converter_running(self) -> bool:
        if not self._hooks.is_operation_active():
            return False

        logger.warning("Conversion is already running. Wait or cancel the current operation.")
        self._dialogs.show_info(
            TAG_MAIN_EXPLORER_DIALOG_CONVERTER_RUNNING,
            self._language_manager["main.explorer.message.converter_running_msg"],
            self._language_manager["main.explorer.title.converter_running_dialog"],
        )

        return True

    def _on_conversion_success(self, success: ConversionSuccess) -> None:
        self._hooks.on_refresh_trees()
        if success.is_single:
            message = self._language_manager["main.converter.message.load_file_prompt"]
            ok_label = self._language_manager["main.converter.label.load_button"]
            path: Optional[Path] = success.written[0]
        else:
            message = self._language_manager["main.converter.message.load_directory_prompt"]
            ok_label = self._language_manager["main.converter.label.open_button"]
            path = None

        self._dialogs.show_confirmation(
            TAG_MAIN_CONVERTER_DIALOG_LOAD,
            message,
            self._language_manager["main.converter.title.load_dialog"],
            self._converter_logic.handle_load_request,
            ok_label=ok_label,
            cancel_label=self._language_manager["main.converter.label.close_button"],
            path=path,
            on_cancel=self._converter_logic.close,
        )

    def _request_output(self, output: OutputKind) -> None:
        """Answers the output switch, asking which recordings to mix where the list overflows one.

        A mix reaches a fixed number of recordings, so a longer list is put to the reader in the
        window that shows what fits already ticked. Every other switch takes effect straight away.
        """
        candidates = self._converter_logic.gathered_paths
        if not output.mixes or len(candidates) <= MAX_STEM_SOURCES:
            self._converter_logic.set_output(output)
            return

        self._stem_selection_window.open(candidates, MAX_STEM_SOURCES)

    def _can_add_stems(self) -> bool:
        """The converter is free to gather recordings into a stems conversion."""
        return not self._hooks.is_operation_active()

    def _on_file_add_requested(self, filepath: Path) -> None:
        """Gathers one recording into a stems conversion, opening one where none is being built."""
        if self._hooks.is_operation_active():
            return

        self._converter_logic.gather_recordings([filepath])

    def _on_directory_add_requested(self, directory_path: Path) -> None:
        """Gathers a folder into the setup, standing for the recordings found below it."""
        if self._hooks.is_operation_active():
            return

        self._converter_logic.gather_folder(directory_path)

    def _request_cancel_confirmation(self) -> None:
        self._dialogs.show_confirmation(
            TAG_MAIN_CONVERTER_DIALOG_CANCEL,
            self._language_manager["main.converter.message.cancel_prompt"],
            self._language_manager["main.converter.title.cancel_dialog"],
            self._converter_logic.cancel,
            ok_label=self._language_manager["main.converter.label.stop_button"],
            cancel_label=self._language_manager["main.converter.label.continue_button"],
        )

    def _update_config_panel_view(self) -> None:
        config = self._config_manager.config
        self._config_panel.update_view(
            ConfigPanelViewModel(
                normalize=config.general.normalize,
                quantize=config.general.quantize,
                sample_rate=config.library.sample_rate,
                nes_frequency=config.library.nes_frequency,
            )
        )

    def _update_reconstructor_panel_view(self) -> None:
        """The settings card reads the choices from the converter and the drive from the config.

        The two owners answer one card, so the composition point is where their readings meet.
        """
        self._reconstructor_panel.update_view(
            ReconstructorPanelViewModel(
                slots=self._converter_logic.settings_slots,
                inspected=self._converter_logic.inspected_name,
                drive=self._config_manager.config.generation.drive,
            )
        )

    def _update_advanced_settings_panel_view(self) -> None:
        self._advanced_settings_panel.update_view(
            AdvancedSettingsPanelViewModel(
                max_workers=self._config_manager.config.general.max_workers,
                spectrum_method=self._config_manager.config.library.spectrum_method,
                transformation_gamma=self._config_manager.config.library.transformation_gamma,
                library_directory=self._config_manager.get_library_directory(),
                reconstructions_directory=self._config_manager.get_reconstructions_directory(),
            )
        )

    def _select_library_directory(self) -> None:
        directory = select_directory_dialog(
            title=self._language_manager["main.advanced.title.select_library_directory"],
            initial_directory=self._advanced_settings_panel.library_directory,
        )
        self._handle_select_library_directory(directory)

    @ignore_none_path
    def _handle_select_library_directory(self, directory: Path) -> None:
        self._advanced_settings_panel.change_library_directory(directory)
        self._session_manager.set_library_path(directory)

    def _select_output_directory(self) -> None:
        directory = select_directory_dialog(
            title=self._language_manager["main.advanced.title.select_output_directory"],
            initial_directory=self._advanced_settings_panel.reconstructions_directory,
        )
        self._handle_select_output_directory(directory)

    @ignore_none_path
    def _handle_select_output_directory(self, directory: Path) -> None:
        self._advanced_settings_panel.change_reconstructions_directory(directory)

    def create_tab(self) -> None:
        with dpg.tab(
            label=self._language_manager["global.menu.label.tab_main"],
            tag=TAG_GLOBAL_TAB_MAIN,
            parent=TAG_GLOBAL_TABS,
        ):
            self._side_panel_count = TabColumns.build(
                panel_gap=self._geometry.panel_gap,
                columns=[
                    ColumnSpec(
                        tag=_LEFT_COLUMN_TAG,
                        build=self._explorer_panel.create_panel,
                        theme=TAG_GLOBAL_THEME_PANEL_SURFACE,
                        width=self._geometry.side_width,
                        height=self._geometry.side_height,
                        no_scrollbar=True,
                    ),
                    ColumnSpec(
                        tag=_CENTER_COLUMN_TAG,
                        build=self._build_center,
                        theme=TAG_GLOBAL_THEME_PANEL_GROUND,
                        border=False,
                    ),
                ],
            )

        self._sync_explorer_width()

    def _build_center(self, parent: str) -> None:
        """Stacks the config and reconstructor cards side by side, then the advanced and converter cards below."""
        TabColumns.row(
            panel_gap=self._geometry.panel_gap,
            height=self._config_height,
            tag=TAG_MAIN_CONFIG_TABLE_CONFIG_ROW,
            columns=[
                ColumnSpec(
                    tag=TAG_MAIN_CONFIG_PANEL_CONFIG_CELL,
                    build=self._config_panel.create_panel,
                ),
                ColumnSpec(
                    tag=TAG_MAIN_RECONSTRUCTOR_PANEL_RECONSTRUCTOR_CELL,
                    build=self._reconstructor_panel.create_panel,
                ),
            ],
        )
        self._sync_config_row_height()
        dpg.add_spacer(height=self._geometry.panel_gap, parent=parent)
        self._advanced_settings_panel.create_panel(parent)
        dpg.add_spacer(height=self._geometry.panel_gap, parent=parent)
        self._converter_panel.create_panel(parent)

    def _wire_collapse_handlers(self) -> None:
        """Routes each Main card's collapse toggle to the handler that persists it and reflows the shared config row."""
        self._explorer_panel.set_collapse_handler(self._on_explorer_collapse_changed)
        self._config_panel.set_collapse_handler(self._on_config_row_collapse_changed)
        self._reconstructor_panel.set_collapse_handler(self._on_config_row_collapse_changed)
        self._advanced_settings_panel.set_collapse_handler(self._on_card_collapse_changed)
        self._converter_panel.set_collapse_handler(self._on_card_collapse_changed)

    def _on_card_collapse_changed(self, card_tag: str, collapsed: bool) -> None:
        """Persists a card's collapsed state so it restores on the next launch."""
        self._session_manager.set_card_collapsed(card_tag, collapsed)

    def _on_explorer_collapse_changed(self, card_tag: str, collapsed: bool) -> None:
        """Persists the filesystem panel's collapse, then docks or restores the width of the column it fills."""
        self._session_manager.set_card_collapsed(card_tag, collapsed)
        self._sync_explorer_width()

    def sync_responsive_layout(self) -> None:
        """Refits this tab's side column to the current viewport, the entry the resize handler calls."""
        self._sync_explorer_width()

    def _sync_explorer_width(self) -> None:
        """Shrinks the filesystem column to the collapse rail when collapsed, else sizes it to the viewport width."""
        if self._explorer_panel.collapsed:
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

    def _on_config_row_collapse_changed(self, card_tag: str, collapsed: bool) -> None:
        """Persists the config or reconstructor collapse, then reflows the row both cards share."""
        self._session_manager.set_card_collapsed(card_tag, collapsed)
        self._sync_config_row_height()

    def _sync_config_row_height(self) -> None:
        """Lets the shared config row size to its collapsed cards once both are collapsed, else keeps it full height."""
        both_collapsed = self._config_panel.collapsed and self._reconstructor_panel.collapsed
        height = 0 if both_collapsed else self._config_height
        dpg_configure_item(TAG_MAIN_CONFIG_TABLE_CONFIG_ROW, height=height)

    def is_converter_active(self) -> bool:
        return self._converter_logic.is_active

    def is_converter_panel_visible(self) -> bool:
        return self._converter_panel.is_visible()

    def refresh_converter_view(self) -> None:
        self._converter_logic.refresh_view()

    def convert_path(self, path: Path) -> None:
        """Converts exactly what a Reconstruct named, replacing whatever the reader gathered."""
        self._converter_logic.convert_path(path)

    def save_browser_shape(self) -> None:
        """Writes down the folders the explorer stands open, so a later run reads down to them."""
        self._session_manager.set_expanded_directories(self._explorer_logic.open_directories)

    def refresh_browser(self) -> None:
        self._explorer_panel.refresh()

    def toggle_channel(self, channel: ChannelName) -> None:
        """Switches one channel in or out of the set a reconstruction is built from."""
        self._reconstructor_panel.toggle_channel(channel)

    def toggle_advanced_settings(self) -> None:
        advanced_settings = self._session_manager.toggle_show_advanced_settings()
        self._advanced_settings_panel.set_visibility(advanced_settings)

    def sync_advanced_settings_visibility(self) -> None:
        self._advanced_settings_panel.set_visibility(self._session_manager.advanced_settings)

    def emit_initial_view(self) -> None:
        self._converter_logic.emit_initial_view()

    def cleanup(self) -> None:
        self._converter_logic.cleanup()
