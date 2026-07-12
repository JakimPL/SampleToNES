from pathlib import Path
from typing import Callable, Optional

import dearpygui.dearpygui as dpg

from sampletones_application.categories.elements.global_ import MenuElements
from sampletones_application.categories.elements.main import (
    ConverterElements,
    ExplorerElements,
)
from sampletones_application.categories.hierarchy import Page, Panel, TextType
from sampletones_application.categories.manager import LanguageManager
from sampletones_application.config.managers.config import ConfigManager
from sampletones_application.config.managers.session import SessionManager
from sampletones_application.coordinators.playback import (
    AudioPlayerProtocol,
    PreviewPlayer,
)
from sampletones_application.layout.config import LayoutConfig
from sampletones_application.logic.instruction.library_manager import (
    InstructionsLibraryManager,
)
from sampletones_application.logic.main.converter import (
    ConversionSuccess,
    ConverterLogic,
)
from sampletones_application.logic.main.explorer import ExplorerLogic
from sampletones_application.logic.shared.tree import TreeLogic
from sampletones_application.services.conversion import ConversionService
from sampletones_application.tags.general import (
    SUF_PANEL_CENTER,
    SUF_PANEL_LEFT,
    TAG_GLOBAL_TAB_MAIN,
    TAG_GLOBAL_TABS,
    TAG_GLOBAL_THEME_PANEL_GROUND,
    TAG_GLOBAL_THEME_PANEL_SURFACE,
)
from sampletones_application.tags.main import (
    TAG_MAIN_CONFIG_PANEL_CONFIG_CELL,
    TAG_MAIN_CONVERTER_DIALOG_CANCEL,
    TAG_MAIN_CONVERTER_DIALOG_LOAD,
    TAG_MAIN_EXPLORER_DIALOG_CONVERTER_RUNNING,
    TAG_MAIN_RECONSTRUCTOR_PANEL_RECONSTRUCTOR_CELL,
)
from sampletones_application.ui.elements.layout.columns import ColumnSpec, TabColumns
from sampletones_application.ui.elements.status import GUIStatusBar
from sampletones_application.ui.elements.tree.colors import TreeColors
from sampletones_application.ui.panels.main.advanced import GUIAdvancedSettingsPanel
from sampletones_application.ui.panels.main.config import GUIConfigPanel
from sampletones_application.ui.panels.main.converter import GUIConverterPanel
from sampletones_application.ui.panels.main.explorer import GUIExplorerPanel
from sampletones_application.ui.panels.main.reconstructor import GUIReconstructorPanel
from sampletones_application.utils.gui.dialogs import DialogsRenderer
from sampletones_application.utils.gui.frame import FrameCallbackManager
from sampletones_application.utils.gui.shortcuts.manager import ShortcutManager
from sampletones_application.view_model.main.advanced import (
    AdvancedSettingsPanelViewModel,
)
from sampletones_application.view_model.main.config import ConfigPanelViewModel
from sampletones_application.view_model.main.converter import ConverterViewModel
from sampletones_application.view_model.main.reconstructor import (
    ReconstructorPanelViewModel,
)
from sampletones_core.audio import AudioDeviceManager
from sampletones_shared.logger import logger
from sampletones_shared.types.callback import PathCallback, VoidCallback


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
        shortcut_manager: ShortcutManager,
        library_manager: InstructionsLibraryManager,
        conversion_service: ConversionService,
        on_reconstruct_file: PathCallback,
        on_reconstruct_directory: PathCallback,
        on_load_reconstruction: Callable[[Optional[Path]], None],
        on_load_library: PathCallback,
        is_operation_active: Callable[[], bool],
        on_busy_state_changed: VoidCallback,
        *,
        layout: LayoutConfig,
        language_manager: LanguageManager,
        dialogs: DialogsRenderer,
        status_bar: GUIStatusBar,
        on_load_file: PathCallback,
        on_load_directory: VoidCallback,
        on_cancelled: VoidCallback,
        on_refresh_trees: VoidCallback,
        on_generate_library: VoidCallback,
    ) -> None:
        self._config_manager = config_manager
        self._session_manager = session_manager
        self._library_manager = library_manager
        self._on_reconstruct_file = on_reconstruct_file
        self._on_reconstruct_directory = on_reconstruct_directory
        self._on_load_reconstruction = on_load_reconstruction
        self._on_load_library = on_load_library
        self._is_operation_active = is_operation_active
        self._on_busy_state_changed = on_busy_state_changed
        self._on_refresh_trees = on_refresh_trees
        self._dialogs = dialogs

        self._tab_label = language_manager[
            Page.GLOBAL,
            Panel.MENU,
            TextType.LABEL,
            MenuElements.TAB_MAIN,
        ]
        self._explorer_width = layout.general.columns.side.width
        self._explorer_height = layout.general.columns.side.height
        self._panel_gap = layout.general.panel_gap
        self._config_height = layout.main.config.height
        _msg_converter_error = language_manager[
            Page.MAIN,
            Panel.CONVERTER,
            TextType.MESSAGE,
            ConverterElements.STATUS_ERROR,
        ]
        _msg_no_files = language_manager[
            Page.MAIN,
            Panel.CONVERTER,
            TextType.MESSAGE,
            ConverterElements.STATUS_NO_FILES,
        ]
        _msg_no_generators = language_manager[
            Page.MAIN,
            Panel.CONVERTER,
            TextType.MESSAGE,
            ConverterElements.STATUS_NO_GENERATORS,
        ]
        self._ttl_progress = language_manager[
            Page.MAIN,
            Panel.CONVERTER,
            TextType.TITLE,
            ConverterElements.PROGRESS_DIALOG,
        ]
        self._ttl_load = language_manager[
            Page.MAIN,
            Panel.CONVERTER,
            TextType.TITLE,
            ConverterElements.LOAD_DIALOG,
        ]
        self._msg_load_file = language_manager[
            Page.MAIN,
            Panel.CONVERTER,
            TextType.MESSAGE,
            ConverterElements.LOAD_FILE_PROMPT,
        ]
        self._msg_load_directory = language_manager[
            Page.MAIN,
            Panel.CONVERTER,
            TextType.MESSAGE,
            ConverterElements.LOAD_DIRECTORY_PROMPT,
        ]
        self._lbl_load = language_manager[
            Page.MAIN,
            Panel.CONVERTER,
            TextType.LABEL,
            ConverterElements.LOAD_BUTTON,
        ]
        self._lbl_open = language_manager[
            Page.MAIN,
            Panel.CONVERTER,
            TextType.LABEL,
            ConverterElements.OPEN_BUTTON,
        ]
        self._lbl_close = language_manager[
            Page.MAIN,
            Panel.CONVERTER,
            TextType.LABEL,
            ConverterElements.CLOSE_BUTTON,
        ]
        self._ttl_cancel = language_manager[
            Page.MAIN,
            Panel.CONVERTER,
            TextType.TITLE,
            ConverterElements.CANCEL_DIALOG,
        ]
        self._msg_cancel = language_manager[
            Page.MAIN,
            Panel.CONVERTER,
            TextType.MESSAGE,
            ConverterElements.CANCEL_PROMPT,
        ]
        self._lbl_stop = language_manager[
            Page.MAIN,
            Panel.CONVERTER,
            TextType.LABEL,
            ConverterElements.STOP_BUTTON,
        ]
        self._lbl_continue = language_manager[
            Page.MAIN,
            Panel.CONVERTER,
            TextType.LABEL,
            ConverterElements.CONTINUE_BUTTON,
        ]
        self._msg_converter_running = language_manager[
            Page.MAIN,
            Panel.EXPLORER,
            TextType.MESSAGE,
            ExplorerElements.CONVERTER_RUNNING_MSG,
        ]
        self._ttl_converter_running = language_manager[
            Page.MAIN,
            Panel.EXPLORER,
            TextType.TITLE,
            ExplorerElements.CONVERTER_RUNNING_DIALOG,
        ]

        self._preview_player: PreviewPlayer = PreviewPlayer(audio_device_manager)
        self._explorer_logic: ExplorerLogic = ExplorerLogic(config_manager, language_manager=language_manager)
        self._explorer_tree_logic: TreeLogic = TreeLogic(
            session_manager,
            audio_device_manager,
            scheduling=layout.behavior.scheduling,
        )
        self._explorer_panel: GUIExplorerPanel = GUIExplorerPanel(
            self._explorer_logic,
            self._explorer_tree_logic,
            shortcut_manager,
            tree_behavior=layout.behavior.main.explorer,
            language_manager=language_manager,
            status_bar=status_bar,
            colors=TreeColors.create(
                layout.general.colors,
                accent=layout.general.colors.paths.hover,
            ),
        )
        self._explorer_tree_logic.on_lock_state_changed = self._explorer_panel.set_tree_enabled
        self._explorer_tree_logic.on_favorite_changed = self._explorer_panel.update_favorite_indicator
        self._explorer_tree_logic.on_search_update_needed = self._explorer_panel.update_tree_visibility
        self._explorer_tree_logic.on_autoplay_error = self._on_explorer_autoplay_error

        _config = config_manager.config
        self._config_panel: GUIConfigPanel = GUIConfigPanel(
            ConfigPanelViewModel(
                normalize=_config.general.normalize,
                quantize=_config.general.quantize,
                sample_rate=_config.library.sample_rate,
                nes_frequency=_config.library.nes_frequency,
                spectrum_method=_config.library.spectrum_method,
                transformation_gamma=_config.library.transformation_gamma,
            ),
            input_width=layout.general.inputs.default_width,
            label_width=layout.general.inputs.label_width,
            panel_height=layout.main.config.height,
            language_manager=language_manager,
            status_bar=status_bar,
        )
        self._reconstructor_panel: GUIReconstructorPanel = GUIReconstructorPanel(
            ReconstructorPanelViewModel(
                generators=frozenset(_config.generation.generators),
                drive=_config.generation.drive,
            ),
            layout=layout.main.reconstructor,
            input_width=layout.general.inputs.default_width,
            label_width=layout.general.inputs.label_width,
            panel_height=layout.main.config.height,
            language_manager=language_manager,
            status_bar=status_bar,
        )
        self._advanced_settings_panel: GUIAdvancedSettingsPanel = GUIAdvancedSettingsPanel(
            AdvancedSettingsPanelViewModel(
                max_workers=_config.general.max_workers,
                library_directory=config_manager.get_library_directory(),
                reconstructions_directory=config_manager.get_reconstructions_directory(),
            ),
            panel_height=layout.main.advanced.height,
            button_height=layout.main.advanced.button_height,
            input_width=layout.general.inputs.default_width,
            label_width=layout.general.inputs.label_width,
            file_dialog_width=layout.general.dialogs.file.width,
            file_dialog_height=layout.general.dialogs.file.height,
            max_workers_minimum=layout.behavior.main.max_workers_minimum,
            language_manager=language_manager,
            status_bar=status_bar,
            path_colors=layout.general.colors.paths,
        )
        self._converter_logic: ConverterLogic = ConverterLogic(
            config_manager,
            conversion_service,
            scheduling=layout.behavior.scheduling,
            language_manager=language_manager,
            is_operation_active=is_operation_active,
        )
        self._converter_panel: GUIConverterPanel = GUIConverterPanel(
            layout=layout.main.converter,
            path_colors=layout.general.colors.paths,
            language_manager=language_manager,
            status_bar=status_bar,
        )

        config_manager.add_config_change_callback(self._update_config_panel_view)
        config_manager.add_config_change_callback(self._update_reconstructor_panel_view)
        config_manager.add_config_change_callback(self._update_advanced_settings_panel_view)

        self._config_panel.on_audio_settings_changed = config_manager.apply_audio_settings
        self._config_panel.on_library_settings_changed = config_manager.apply_library_settings
        self._reconstructor_panel.on_generation_settings_changed = config_manager.apply_generation_settings
        self._advanced_settings_panel.on_advanced_settings_changed = config_manager.apply_advanced_settings
        self._advanced_settings_panel.on_library_path_memorized = session_manager.set_library_path

        self._explorer_panel.set_callbacks(
            on_wave_file_clicked=self._on_wave_file_clicked,
            on_directory_clicked=self._on_directory_clicked,
            on_reconstruct_file=self._request_reconstruct_file,
            on_reconstruct_directory=self._request_reconstruct_directory,
            on_load_reconstruction=on_load_reconstruction,
            on_load_library=on_load_library,
            on_set_as_library_directory=self._advanced_settings_panel.change_library_directory,
            on_set_as_reconstructions_directory=self._advanced_settings_panel.change_reconstructions_directory,
        )

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
        self._converter_logic.is_library_available = library_manager.is_library_available_for_config
        self._converter_logic.cancel_library_generation = library_manager.cancel_generation
        self._converter_logic.on_load_file = on_load_file
        self._converter_logic.on_load_directory = on_load_directory
        self._converter_logic.on_cancelled = on_cancelled
        self._converter_logic.generate_library = on_generate_library
        library_manager.on_generation_progress_extra = conversion_service.forward_library_progress

        self._converter_panel.on_convert_requested = self._converter_logic.start_conversion
        self._converter_panel.on_cancel_requested = self._request_cancel_confirmation

    def _on_explorer_autoplay_error(self, exception: Exception) -> None:
        FrameCallbackManager.set_frame_callback(lambda: self._dialogs.show_error(exception))

    def _on_converter_view_changed(self, view_model: ConverterViewModel) -> None:
        self._converter_panel.update_view(view_model)
        self._on_busy_state_changed()

    def _on_wave_file_clicked(self, filepath: Path) -> None:
        if not self._is_operation_active():
            self._converter_logic.set_input_path(filepath, convert=False)

    def _on_directory_clicked(self, directory_path: Path) -> None:
        if not self._is_operation_active():
            self._converter_logic.set_input_path(directory_path, convert=False)

    def _request_reconstruct_file(self, filepath: Path) -> None:
        if self._notify_converter_running():
            return

        self._on_reconstruct_file(filepath)

    def _request_reconstruct_directory(self, directory_path: Path) -> None:
        if self._notify_converter_running():
            return

        self._on_reconstruct_directory(directory_path)

    def _notify_converter_running(self) -> bool:
        if not self._is_operation_active():
            return False

        logger.warning("Conversion is already running. Wait or cancel the current operation.")
        self._dialogs.show_info(
            TAG_MAIN_EXPLORER_DIALOG_CONVERTER_RUNNING,
            self._msg_converter_running,
            self._ttl_converter_running,
        )

        return True

    def _on_conversion_success(self, success: ConversionSuccess) -> None:
        self._on_refresh_trees()
        if success.is_file:
            message = self._msg_load_file
            ok_label = self._lbl_load
            path = success.output_path
        else:
            message = self._msg_load_directory
            ok_label = self._lbl_open
            path = None

        self._dialogs.show_confirmation(
            TAG_MAIN_CONVERTER_DIALOG_LOAD,
            message,
            self._ttl_load,
            self._converter_logic.handle_load_request,
            ok_label=ok_label,
            cancel_label=self._lbl_close,
            path=path,
            on_cancel=self._converter_logic.close,
        )

    def _request_cancel_confirmation(self) -> None:
        self._dialogs.show_confirmation(
            TAG_MAIN_CONVERTER_DIALOG_CANCEL,
            self._msg_cancel,
            self._ttl_cancel,
            self._converter_logic.cancel,
            ok_label=self._lbl_stop,
            cancel_label=self._lbl_continue,
        )

    def _update_config_panel_view(self) -> None:
        config = self._config_manager.config
        self._config_panel.update_view(
            ConfigPanelViewModel(
                normalize=config.general.normalize,
                quantize=config.general.quantize,
                sample_rate=config.library.sample_rate,
                nes_frequency=config.library.nes_frequency,
                spectrum_method=config.library.spectrum_method,
                transformation_gamma=config.library.transformation_gamma,
            )
        )

    def _update_reconstructor_panel_view(self) -> None:
        config = self._config_manager.config
        self._reconstructor_panel.update_view(
            ReconstructorPanelViewModel(
                generators=frozenset(config.generation.generators),
                drive=config.generation.drive,
            )
        )

    def _update_advanced_settings_panel_view(self) -> None:
        self._advanced_settings_panel.update_view(
            AdvancedSettingsPanelViewModel(
                max_workers=self._config_manager.config.general.max_workers,
                library_directory=self._config_manager.get_library_directory(),
                reconstructions_directory=self._config_manager.get_reconstructions_directory(),
            )
        )

    def create_tab(self) -> None:
        with dpg.tab(
            label=self._tab_label,
            tag=TAG_GLOBAL_TAB_MAIN,
            parent=TAG_GLOBAL_TABS,
        ):
            TabColumns.build(
                panel_gap=self._panel_gap,
                columns=[
                    ColumnSpec(
                        tag=f"{TAG_GLOBAL_TAB_MAIN}{SUF_PANEL_LEFT}",
                        build=self._explorer_panel.create_panel,
                        theme=TAG_GLOBAL_THEME_PANEL_SURFACE,
                        width=self._explorer_width,
                        height=self._explorer_height,
                        no_scrollbar=True,
                    ),
                    ColumnSpec(
                        tag=f"{TAG_GLOBAL_TAB_MAIN}{SUF_PANEL_CENTER}",
                        build=self._build_center,
                        theme=TAG_GLOBAL_THEME_PANEL_GROUND,
                        border=False,
                    ),
                ],
            )

    def _build_center(self, parent: str) -> None:
        """Stacks the config and reconstructor cards side by side, then the advanced and converter cards below."""
        TabColumns.row(
            panel_gap=self._panel_gap,
            height=self._config_height,
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
        dpg.add_spacer(height=self._panel_gap, parent=parent)
        self._advanced_settings_panel.create_panel(parent)
        dpg.add_spacer(height=self._panel_gap, parent=parent)
        self._converter_panel.create_panel(parent)

    @property
    def player(self) -> AudioPlayerProtocol:
        return self._preview_player

    def is_converter_active(self) -> bool:
        return self._converter_logic.is_active

    def is_converter_panel_visible(self) -> bool:
        return self._converter_panel.is_visible()

    def refresh_converter_view(self) -> None:
        self._converter_logic.refresh_view()

    def set_input_path(self, path: Path, convert: bool) -> None:
        self._converter_logic.set_input_path(path, convert=convert)

    def refresh_browser(self) -> None:
        self._explorer_panel.refresh()

    def toggle_advanced_settings(self) -> None:
        advanced_settings = self._session_manager.toggle_show_advanced_settings()
        self._advanced_settings_panel.set_visibility(advanced_settings)

    def sync_advanced_settings_visibility(self) -> None:
        self._advanced_settings_panel.set_visibility(self._session_manager.advanced_settings)

    def emit_initial_view(self) -> None:
        self._converter_logic.emit_initial_view()

    def cleanup(self) -> None:
        self._converter_logic.cleanup()
