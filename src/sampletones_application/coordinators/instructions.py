from pathlib import Path

import dearpygui.dearpygui as dpg

from sampletones_application.config.application.manager import ApplicationConfigManager
from sampletones_application.config.manager import ConfigManager
from sampletones_application.constants.general import (
    SUF_PANEL_CENTER,
    SUF_PANEL_LEFT,
    SUF_PANEL_RIGHT,
    TAG_TAB_GLOBAL_INSTRUCTIONS,
    TAG_TABS_GLOBAL,
)
from sampletones_application.coordinators.playback import AudioPlayerPanelProtocol
from sampletones_application.layout.config import LayoutConfig
from sampletones_application.logic.instruction.details import InstructionDetailsPanelLogic
from sampletones_application.logic.instruction.library import LibraryLogic
from sampletones_application.logic.instruction.library_manager import InstructionsLibraryManager
from sampletones_application.logic.shared.player import PlayerLogic
from sampletones_application.text.elements.global_ import MenuElements
from sampletones_application.text.elements.instructions import InstructionsLibraryElements
from sampletones_application.text.hierarchy import Page, Panel, TextType
from sampletones_application.text.key import TextKey
from sampletones_application.text.manager import LanguageManager
from sampletones_application.ui.panels.instruction.details import GUIInstructionDetailsPanel
from sampletones_application.ui.panels.instruction.instruction import GUIInstructionPanel
from sampletones_application.ui.panels.instruction.library import GUIInstructionsLibraryPanel
from sampletones_application.utils.dialogs import show_error_dialog
from sampletones_application.utils.shortcuts.manager import ShortcutManager
from sampletones_application.view_model.instruction.data import InstructionPanelData
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
        *,
        layout: LayoutConfig,
        language_manager: LanguageManager,
    ) -> None:
        self._config_manager = config_manager
        self._application_config_manager = application_config_manager
        self._audio_device_manager = audio_device_manager
        self._shortcut_manager = shortcut_manager
        self._library_manager = library_manager
        self._on_audio_state_changed = on_audio_state_changed

        self._tab_label = language_manager[
            TextKey(Page.GLOBAL, Panel.MENU, TextType.LABEL, MenuElements.TAB_INSTRUCTIONS)
        ]
        self._left_width = layout.general.panels.left.width
        self._left_height = layout.general.panels.left.height
        self._details_width = layout.general.panels.instructions_details.width
        self._right_height = layout.general.panels.right.height
        self._msg_display_error = language_manager[
            TextKey(
                Page.INSTRUCTIONS, Panel.LIBRARY, TextType.MESSAGE, InstructionsLibraryElements.STATUS_DISPLAY_ERROR
            )
        ]

        self._library_logic = LibraryLogic(config_manager, library_manager, language_manager=language_manager)
        self._library_panel = GUIInstructionsLibraryPanel(
            self._library_logic,
            application_config_manager,
            audio_device_manager,
            shortcut_manager,
            scheduling=layout.behavior.scheduling,
            tree_behavior=layout.behavior.instructions,
            language_manager=language_manager,
        )
        self._instruction_player_logic = PlayerLogic(audio_device_manager, on_audio_state_changed)
        self._instruction_panel = GUIInstructionPanel(
            self._instruction_player_logic,
            layout=layout.graphs,
            layout_player=layout.player,
            language_manager=language_manager,
        )
        self._instruction_details_logic = InstructionDetailsPanelLogic(
            library_manager,
            layout=layout.instructions,
            language_manager=language_manager,
        )
        self._instruction_details_panel = GUIInstructionDetailsPanel(
            layout=layout.instructions,
            language_manager=language_manager,
        )

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
            show_error_dialog(exception, self._msg_display_error)
        self._on_audio_state_changed()

    def create_tab(self) -> None:
        with dpg.tab(
            tag=TAG_TAB_GLOBAL_INSTRUCTIONS,
            parent=TAG_TABS_GLOBAL,
            label=self._tab_label,
        ):
            with dpg.table(
                parent=TAG_TAB_GLOBAL_INSTRUCTIONS,
                header_row=False,
                resizable=False,
                policy=dpg.mvTable_SizingStretchProp,
            ):
                dpg.add_table_column(width_fixed=True)
                dpg.add_table_column()
                dpg.add_table_column(width_fixed=True)

                with dpg.table_row():
                    with dpg.child_window(
                        tag=f"{TAG_TAB_GLOBAL_INSTRUCTIONS}{SUF_PANEL_LEFT}",
                        width=self._left_width,
                        height=self._left_height,
                        no_scrollbar=True,
                        no_scroll_with_mouse=True,
                    ):
                        self._library_panel.create_panel()

                    with dpg.child_window(
                        tag=f"{TAG_TAB_GLOBAL_INSTRUCTIONS}{SUF_PANEL_CENTER}",
                        no_scroll_with_mouse=True,
                    ):
                        self._instruction_panel.create_panel()

                    with dpg.child_window(
                        tag=f"{TAG_TAB_GLOBAL_INSTRUCTIONS}{SUF_PANEL_RIGHT}",
                        width=self._details_width,
                        height=self._right_height,
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
    def player_panel(self) -> AudioPlayerPanelProtocol:
        return self._instruction_panel.player_panel
