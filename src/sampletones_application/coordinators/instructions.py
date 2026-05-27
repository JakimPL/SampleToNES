from pathlib import Path

import dearpygui.dearpygui as dpg

from sampletones_application.config.application.manager import ApplicationConfigManager
from sampletones_application.config.manager import ConfigManager
from sampletones_application.constants.general import (
    DIM_PANEL_HEIGHT_LEFT,
    DIM_PANEL_HEIGHT_RIGHT,
    DIM_PANEL_WIDTH_INSTRUCTIONS_DETAILS,
    DIM_PANEL_WIDTH_LEFT,
    LBL_TAB_INSTRUCTIONS,
    SUF_PANEL_CENTER,
    SUF_PANEL_LEFT,
    SUF_PANEL_RIGHT,
    TAG_TAB_INSTRUCTIONS,
    TAG_TABS,
)
from sampletones_application.constants.instructions import MSG_LIBRARY_DISPLAY_ERROR
from sampletones_application.logic.instruction.data import InstructionPanelData
from sampletones_application.logic.instruction.details import InstructionDetailsPanelLogic
from sampletones_application.logic.library.library import LibraryLogic
from sampletones_application.logic.library.manager import InstructionsLibraryManager
from sampletones_application.logic.player.player import PlayerLogic
from sampletones_application.ui.panels.instruction.details.panel import GUIInstructionDetailsPanel
from sampletones_application.ui.panels.instruction.instruction.panel import GUIInstructionPanel
from sampletones_application.ui.panels.instruction.library.panel import GUIInstructionsLibraryPanel
from sampletones_application.ui.panels.player import GUIAudioPlayerPanel
from sampletones_application.utils.dialogs import show_error_dialog
from sampletones_application.utils.shortcuts.manager import ShortcutManager
from sampletones_core.audio import AudioDeviceManager
from sampletones_shared.exceptions import LibraryDisplayError
from sampletones_shared.types.callback import VoidCallback


class InstructionsTabCoordinator:
    def __init__(
        self,
        config_manager: ConfigManager,
        application_config_manager: ApplicationConfigManager,
        audio_device_manager: AudioDeviceManager,
        shortcut_manager: ShortcutManager,
        library_manager: InstructionsLibraryManager,
        on_audio_state_changed: VoidCallback,
    ) -> None:
        self._config_manager = config_manager
        self._application_config_manager = application_config_manager
        self._audio_device_manager = audio_device_manager
        self._shortcut_manager = shortcut_manager
        self._library_manager = library_manager
        self._on_audio_state_changed = on_audio_state_changed

        self._library_logic = LibraryLogic(config_manager, library_manager)
        self._library_panel = GUIInstructionsLibraryPanel(
            self._library_logic,
            application_config_manager,
            audio_device_manager,
            shortcut_manager,
        )
        self._instruction_player_logic = PlayerLogic(audio_device_manager, on_audio_state_changed)
        self._instruction_panel = GUIInstructionPanel(self._instruction_player_logic)
        self._instruction_details_logic = InstructionDetailsPanelLogic(library_manager)
        self._instruction_details_panel = GUIInstructionDetailsPanel()

        config_manager.add_config_change_callback(self._library_logic.update_status)

        self._library_logic.set_callbacks(
            on_apply_library_config=config_manager.apply_library_config,
            on_instruction_loaded=self._on_instruction_loaded,
        )
        self._instruction_panel.set_callbacks(
            on_clear_instruction_details=self._instruction_details_logic.clear_display,
        )
        self._instruction_details_logic.on_view_changed = self._instruction_details_panel.update_view
        self._instruction_details_logic.on_instruction_changed = self._instruction_panel.display_instruction
        self._instruction_details_panel.on_instruction_parameter_changed = (
            self._instruction_details_logic.handle_instruction_parameter_changed
        )

    def _on_instruction_loaded(self, instruction_data: InstructionPanelData) -> None:
        try:
            self._instruction_panel.display_instruction(instruction_data)
            self._instruction_details_logic.display_instruction(instruction_data)
        except LibraryDisplayError as exception:
            show_error_dialog(exception, MSG_LIBRARY_DISPLAY_ERROR)
        self._on_audio_state_changed()

    def create_tab(self) -> None:
        with dpg.tab(
            tag=TAG_TAB_INSTRUCTIONS,
            parent=TAG_TABS,
            label=LBL_TAB_INSTRUCTIONS,
        ):
            with dpg.table(
                parent=TAG_TAB_INSTRUCTIONS,
                header_row=False,
                resizable=False,
                policy=dpg.mvTable_SizingStretchProp,
            ):
                dpg.add_table_column(width_fixed=True)
                dpg.add_table_column()
                dpg.add_table_column(width_fixed=True)

                with dpg.table_row():
                    with dpg.child_window(
                        tag=f"{TAG_TAB_INSTRUCTIONS}{SUF_PANEL_LEFT}",
                        width=DIM_PANEL_WIDTH_LEFT,
                        height=DIM_PANEL_HEIGHT_LEFT,
                        no_scrollbar=True,
                        no_scroll_with_mouse=True,
                    ):
                        self._library_panel.create_panel()

                    with dpg.child_window(
                        tag=f"{TAG_TAB_INSTRUCTIONS}{SUF_PANEL_CENTER}",
                        no_scroll_with_mouse=True,
                    ):
                        self._instruction_panel.create_panel()

                    with dpg.child_window(
                        tag=f"{TAG_TAB_INSTRUCTIONS}{SUF_PANEL_RIGHT}",
                        width=DIM_PANEL_WIDTH_INSTRUCTIONS_DETAILS,
                        height=DIM_PANEL_HEIGHT_RIGHT,
                        no_scrollbar=True,
                        no_scroll_with_mouse=True,
                    ):
                        self._instruction_details_panel.create_panel()

    def ensure_library_loaded(self) -> None:
        if not self._library_manager.does_library_exist():
            self._library_panel.generate_library()
        self._library_panel.load_current_library()

    def load_library_file(self, filepath: Path) -> None:
        self._instruction_panel.close_instruction()
        self._library_panel.load_library_file(filepath)

    def close_instruction(self) -> None:
        self._instruction_panel.close_instruction()

    def is_library_generating(self) -> bool:
        return self._library_panel.is_library_generating()

    @property
    def player_panel(self) -> GUIAudioPlayerPanel:
        return self._instruction_panel.player_panel
