from pathlib import Path
from typing import Callable, Optional

import dearpygui.dearpygui as dpg

from sampletones_application.categories.elements.global_ import MenuElements
from sampletones_application.categories.elements.main import ConverterElements
from sampletones_application.categories.hierarchy import Page, Panel, TextType
from sampletones_application.categories.manager import LanguageManager
from sampletones_application.config.application.manager import SessionManager
from sampletones_application.config.manager import ConfigManager
from sampletones_application.constants.general import (
    SUF_PANEL_CENTER,
    SUF_PANEL_LEFT,
    TAG_GLOBAL_TAB_MAIN,
    TAG_GLOBAL_TABS,
)
from sampletones_application.layout.config import LayoutConfig
from sampletones_application.logic.instruction.library_manager import InstructionsLibraryManager
from sampletones_application.logic.main.converter import ConverterLogic
from sampletones_application.logic.main.explorer import ExplorerLogic
from sampletones_application.services.conversion import ConversionService
from sampletones_application.ui.panels.main.advanced import GUIAdvancedSettingsPanel
from sampletones_application.ui.panels.main.config import GUIConfigPanel
from sampletones_application.ui.panels.main.converter.converter import GUIConverterPanel
from sampletones_application.ui.panels.main.converter.success_dialog import ConverterSuccessDialog
from sampletones_application.ui.panels.main.explorer import GUIExplorerPanel
from sampletones_application.ui.panels.main.main import GUIMainPanel
from sampletones_application.ui.panels.main.reconstructor import GUIReconstructorPanel
from sampletones_application.utils.dialogs import DialogsRenderer
from sampletones_application.utils.shortcuts.manager import ShortcutManager
from sampletones_application.view_model.main.advanced import AdvancedSettingsPanelViewModel
from sampletones_application.view_model.main.config import ConfigPanelViewModel
from sampletones_application.view_model.main.reconstructor import ReconstructorPanelViewModel
from sampletones_core.audio import AudioDeviceManager
from sampletones_shared.types.callback import PathCallback


class MainTabCoordinator:
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
        is_generation_in_progress: Callable[[], bool],
        *,
        layout: LayoutConfig,
        language_manager: LanguageManager,
        dialogs: DialogsRenderer,
    ) -> None:
        self._config_manager = config_manager
        self._session_manager = session_manager
        self._library_manager = library_manager
        self._on_reconstruct_file = on_reconstruct_file
        self._on_reconstruct_directory = on_reconstruct_directory
        self._on_load_reconstruction = on_load_reconstruction
        self._on_load_library = on_load_library
        self._is_generation_in_progress = is_generation_in_progress

        self._tab_label = language_manager[
            Page.GLOBAL,
            Panel.MENU,
            TextType.LABEL,
            MenuElements.TAB_MAIN,
        ]
        self._explorer_width = layout.main.explorer.width
        self._explorer_height = layout.main.explorer.height
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
        _title_progress = language_manager[
            Page.MAIN,
            Panel.CONVERTER,
            TextType.TITLE,
            ConverterElements.PROGRESS_DIALOG,
        ]

        self._explorer_logic: ExplorerLogic = ExplorerLogic(config_manager, language_manager=language_manager)
        self._explorer_panel: GUIExplorerPanel = GUIExplorerPanel(
            self._explorer_logic,
            session_manager,
            audio_device_manager,
            shortcut_manager,
            scheduling=layout.behavior.scheduling,
            tree_behavior=layout.behavior.main.explorer,
            language_manager=language_manager,
            dialogs=dialogs,
            favorite_color=layout.general.colors.favorites.default,
            node_color=layout.general.colors.paths.hover,
        )

        _config = config_manager.config
        self._config_panel: GUIConfigPanel = GUIConfigPanel(
            ConfigPanelViewModel(
                normalize=_config.general.normalize,
                quantize=_config.general.quantize,
                sample_rate=_config.library.sample_rate,
                change_rate=_config.library.change_rate,
                transformation_gamma=_config.library.transformation_gamma,
            ),
            input_width=layout.general.inputs.default_width,
            panel_height=layout.main.config.height,
            language_manager=language_manager,
        )
        self._reconstructor_panel: GUIReconstructorPanel = GUIReconstructorPanel(
            ReconstructorPanelViewModel(
                generators=frozenset(_config.generation.generators),
                mixer=_config.generation.mixer,
            ),
            input_width=layout.general.inputs.default_width,
            panel_height=layout.main.config.height,
            language_manager=language_manager,
        )
        self._advanced_settings_panel: GUIAdvancedSettingsPanel = GUIAdvancedSettingsPanel(
            AdvancedSettingsPanelViewModel(
                max_workers=_config.general.max_workers,
                library_directory=config_manager.get_library_directory(),
                output_directory=config_manager.get_output_directory(),
            ),
            panel_height=layout.main.advanced.height,
            input_width=layout.general.inputs.default_width,
            file_dialog_width=layout.general.dialogs.file.width,
            file_dialog_height=layout.general.dialogs.file.height,
            max_workers_minimum=layout.behavior.main.max_workers_minimum,
            language_manager=language_manager,
            path_colors=layout.general.colors.paths,
        )
        self._converter_logic: ConverterLogic = ConverterLogic(
            config_manager,
            conversion_service,
            scheduling=layout.behavior.scheduling,
            language_manager=language_manager,
        )
        self._converter_panel: GUIConverterPanel = GUIConverterPanel(
            layout=layout.main.converter,
            path_colors=layout.general.colors.paths,
            language_manager=language_manager,
        )
        self._converter_success_dialog: ConverterSuccessDialog = ConverterSuccessDialog(
            language_manager=language_manager,
            dialogs=dialogs,
        )
        self._main_panel: GUIMainPanel = GUIMainPanel(
            self._config_panel,
            self._reconstructor_panel,
            self._advanced_settings_panel,
            self._converter_panel,
            layout=layout.main,
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
            on_reconstruct_file=on_reconstruct_file,
            on_reconstruct_directory=on_reconstruct_directory,
            on_load_reconstruction=on_load_reconstruction,
            on_load_library=on_load_library,
            on_set_as_library_directory=self._advanced_settings_panel.change_library_directory,
            on_set_as_output_directory=self._advanced_settings_panel.change_output_directory,
            is_converter_running=is_generation_in_progress,
        )

        self._converter_logic.on_view_changed = self._converter_panel.update_view
        self._converter_logic.on_success = self._converter_success_dialog.show
        self._converter_logic.on_error = lambda error: dialogs.show_error(error, _msg_converter_error)
        self._converter_logic.on_no_files_to_process = lambda: dialogs.show_info(
            self._converter_panel.tag,
            _msg_no_files,
            _title_progress,
        )
        self._converter_logic.is_library_loaded = library_manager.is_library_loaded
        library_manager.on_generation_progress_extra = conversion_service.forward_library_progress

        self._converter_panel.on_convert_requested = self._converter_logic.start_conversion
        self._converter_panel.on_cancel_requested = self._converter_logic.cancel
        self._converter_panel.on_close_requested = self._converter_logic.close
        self._converter_panel.on_load_requested = self._converter_logic.handle_load_request

    def _on_wave_file_clicked(self, filepath: Path) -> None:
        if not self._is_generation_in_progress():
            self._converter_logic.set_input_path(filepath, convert=False)

    def _on_directory_clicked(self, directory_path: Path) -> None:
        if not self._is_generation_in_progress():
            self._converter_logic.set_input_path(directory_path, convert=False)

    def _update_config_panel_view(self) -> None:
        config = self._config_manager.config
        self._config_panel.update_view(
            ConfigPanelViewModel(
                normalize=config.general.normalize,
                quantize=config.general.quantize,
                sample_rate=config.library.sample_rate,
                change_rate=config.library.change_rate,
                transformation_gamma=config.library.transformation_gamma,
            )
        )

    def _update_reconstructor_panel_view(self) -> None:
        config = self._config_manager.config
        self._reconstructor_panel.update_view(
            ReconstructorPanelViewModel(
                generators=frozenset(config.generation.generators),
                mixer=config.generation.mixer,
            )
        )

    def _update_advanced_settings_panel_view(self) -> None:
        self._advanced_settings_panel.update_view(
            AdvancedSettingsPanelViewModel(
                max_workers=self._config_manager.config.general.max_workers,
                library_directory=self._config_manager.get_library_directory(),
                output_directory=self._config_manager.get_output_directory(),
            )
        )

    def create_tab(self) -> None:
        with dpg.tab(
            label=self._tab_label,
            tag=TAG_GLOBAL_TAB_MAIN,
            parent=TAG_GLOBAL_TABS,
        ):
            with dpg.table(
                header_row=False,
                resizable=False,
                policy=dpg.mvTable_SizingStretchProp,
            ):
                dpg.add_table_column(width_fixed=True)
                dpg.add_table_column()

                with dpg.table_row():
                    with dpg.child_window(
                        tag=f"{TAG_GLOBAL_TAB_MAIN}{SUF_PANEL_LEFT}",
                        width=self._explorer_width,
                        height=self._explorer_height,
                        no_scrollbar=True,
                        no_scroll_with_mouse=True,
                    ):
                        self._explorer_panel.create_panel()

                    with dpg.child_window(
                        tag=f"{TAG_GLOBAL_TAB_MAIN}{SUF_PANEL_CENTER}",
                        no_scroll_with_mouse=True,
                    ):
                        self._main_panel.create_panel()

    def is_converter_running(self) -> bool:
        return self._converter_logic.is_running()

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

    @property
    def converter_logic(self) -> ConverterLogic:
        return self._converter_logic
