from pathlib import Path
from typing import Callable

import dearpygui.dearpygui as dpg

from sampletones_application.categories.elements.global_ import MenuElements
from sampletones_application.categories.elements.instructions import (
    InstructionsLibraryElements,
)
from sampletones_application.categories.hierarchy import Page, Panel, TextType
from sampletones_application.categories.manager import LanguageManager
from sampletones_application.config.managers.config import ConfigManager
from sampletones_application.config.managers.session import SessionManager
from sampletones_application.constants.general import (
    SUF_PANEL_CENTER,
    SUF_PANEL_LEFT,
    SUF_PANEL_RIGHT,
    TAG_GLOBAL_TAB_INSTRUCTIONS,
    TAG_GLOBAL_TABS,
)
from sampletones_application.constants.instructions import (
    TAG_INSTRUCTIONS_LIBRARY_DIALOG_REGENERATE_CONFIRMATION,
    TAG_INSTRUCTIONS_LIBRARY_PANEL,
)
from sampletones_application.coordinators.playback import AudioPlayerPanelProtocol
from sampletones_application.layout.config import LayoutConfig
from sampletones_application.logic.instruction.details import (
    InstructionDetailsPanelLogic,
)
from sampletones_application.logic.instruction.library import LibraryLogic
from sampletones_application.logic.instruction.library_manager import (
    InstructionsLibraryManager,
)
from sampletones_application.logic.shared.player import PlayerLogic
from sampletones_application.logic.shared.tree import TreeLogic
from sampletones_application.ui.elements.tree.colors import TreeColors
from sampletones_application.ui.panels.instruction.details import (
    GUIInstructionDetailsPanel,
)
from sampletones_application.ui.panels.instruction.instruction import (
    GUIInstructionPanel,
)
from sampletones_application.ui.panels.instruction.library import (
    GUIInstructionsLibraryPanel,
)
from sampletones_application.utils.gui.dialogs import DialogsRenderer
from sampletones_application.utils.gui.frame import FrameCallbackManager
from sampletones_application.utils.gui.shortcuts.manager import ShortcutManager
from sampletones_application.view_model.instruction.data import InstructionPanelData
from sampletones_core.audio import AudioDeviceManager
from sampletones_core.constants.enums import LibraryGeneratorName
from sampletones_core.library import InstructionLibraryKey
from sampletones_shared.exceptions import LibraryDisplayError
from sampletones_shared.types.callback import VoidCallback


class InstructionsTabCoordinator:
    def __init__(
        self,
        config_manager: ConfigManager,
        session_manager: SessionManager,
        audio_device_manager: AudioDeviceManager,
        shortcut_manager: ShortcutManager,
        library_manager: InstructionsLibraryManager,
        on_audio_state_changed: VoidCallback,
        on_generation_state_changed: VoidCallback,
        is_operation_active: Callable[[], bool],
        is_converter_visible: Callable[[], bool],
        *,
        layout: LayoutConfig,
        language_manager: LanguageManager,
        dialogs: DialogsRenderer,
    ) -> None:
        self._config_manager = config_manager
        self._session_manager = session_manager
        self._audio_device_manager = audio_device_manager
        self._shortcut_manager = shortcut_manager
        self._library_manager = library_manager
        self._on_audio_state_changed = on_audio_state_changed
        self._is_converter_visible = is_converter_visible
        self._dialogs = dialogs

        self._tab_label = language_manager[
            Page.GLOBAL,
            Panel.MENU,
            TextType.LABEL,
            MenuElements.TAB_INSTRUCTIONS,
        ]
        self._left_width = layout.general.panels.left.width
        self._left_height = layout.general.panels.left.height
        self._details_width = layout.general.panels.instructions_details.width
        self._right_height = layout.general.panels.right.height
        self._msg_display_error = language_manager[
            Page.INSTRUCTIONS,
            Panel.LIBRARY,
            TextType.MESSAGE,
            InstructionsLibraryElements.STATUS_DISPLAY_ERROR,
        ]
        self._lbl_regenerate_confirmation_ok = language_manager[
            Page.INSTRUCTIONS,
            Panel.LIBRARY,
            TextType.LABEL,
            InstructionsLibraryElements.REGENERATE_CONFIRMATION_OK,
        ]
        self._msg_regenerate_confirmation = language_manager[
            Page.INSTRUCTIONS,
            Panel.LIBRARY,
            TextType.MESSAGE,
            InstructionsLibraryElements.REGENERATE_CONFIRMATION_MESSAGE,
        ]
        self._ttl_regenerate_confirmation = language_manager[
            Page.INSTRUCTIONS,
            Panel.LIBRARY,
            TextType.TITLE,
            InstructionsLibraryElements.REGENERATE_CONFIRMATION_DIALOG,
        ]
        self._msg_generation_cancelled = language_manager[
            Page.INSTRUCTIONS,
            Panel.LIBRARY,
            TextType.MESSAGE,
            InstructionsLibraryElements.STATUS_GENERATION_CANCELLED,
        ]
        self._msg_generation_failed = language_manager[
            Page.INSTRUCTIONS,
            Panel.LIBRARY,
            TextType.MESSAGE,
            InstructionsLibraryElements.STATUS_GENERATION_FAILED,
        ]
        self._msg_generation_success = language_manager[
            Page.INSTRUCTIONS,
            Panel.LIBRARY,
            TextType.MESSAGE,
            InstructionsLibraryElements.STATUS_GENERATION_SUCCESS,
        ]
        self._ttl_generation_status = language_manager[
            Page.INSTRUCTIONS,
            Panel.LIBRARY,
            TextType.TITLE,
            InstructionsLibraryElements.GENERATION_STATUS_DIALOG,
        ]

        self._library_logic = LibraryLogic(
            config_manager,
            library_manager,
            language_manager=language_manager,
            is_operation_active=is_operation_active,
        )
        self._library_tree_logic = TreeLogic(
            session_manager,
            audio_device_manager,
            scheduling=layout.behavior.scheduling,
        )
        self._library_panel = GUIInstructionsLibraryPanel(
            self._library_logic,
            self._library_tree_logic,
            shortcut_manager,
            tree_behavior=layout.behavior.instructions,
            language_manager=language_manager,
            colors=TreeColors.create(
                layout.general.colors,
                accent=layout.general.colors.headers.library,
            ),
            is_operation_active=is_operation_active,
        )
        self._library_tree_logic.on_lock_state_changed = self._library_panel.set_tree_enabled
        self._library_tree_logic.on_favorite_changed = self._library_panel.update_favorite_indicator
        self._library_tree_logic.on_search_update_needed = self._library_panel.update_tree_visibility

        self._library_logic.configure_lock(
            self._library_tree_logic.lock,
            self._library_tree_logic.unlock,
            lambda: self._library_tree_logic.locked,
        )
        self._library_logic.on_rebuild_tree_needed = self._library_panel.rebuild_tree
        self._library_logic.on_view_changed = self._library_panel.update_view
        self._library_logic.on_generation_completed = self._on_generation_completed
        self._library_logic.on_generation_error = self._on_generation_error
        self._library_logic.on_generation_cancelled = self._on_generation_cancelled
        self._library_logic.on_load_file_not_found = self._on_library_file_not_found
        self._library_logic.on_load_error = self._on_library_load_error

        self._library_panel.on_refresh_requested = self._library_logic.refresh_libraries
        self._library_panel.on_generate_requested = self._request_generate_library
        self._library_panel.on_cancel_generation = self._library_logic.cancel_generation
        self._library_panel.on_library_selected = self._library_logic.load_library_and_set_current
        self._library_panel.on_generator_selected = self._on_generator_selected
        self._instruction_player_logic = PlayerLogic(
            audio_device_manager,
            on_audio_state_changed,
        )
        self._instruction_panel = GUIInstructionPanel(
            self._instruction_player_logic,
            layout=layout.graphs,
            layout_player=layout.player,
            language_manager=language_manager,
            dialogs=dialogs,
        )
        self._instruction_details_logic = InstructionDetailsPanelLogic(
            library_manager,
            layout=layout.instructions,
            language_manager=language_manager,
        )
        self._instruction_details_panel = GUIInstructionDetailsPanel(
            shortcut_manager,
            layout=layout.instructions,
            general_layout=layout.general,
            table_colors=layout.general.colors.tables,
            table_layout=layout.general.tables,
            language_manager=language_manager,
        )

        config_manager.add_config_change_callback(self._library_logic.update_status)

        self._library_logic.set_callbacks(
            on_apply_library_config=config_manager.apply_library_config,
            on_instruction_loaded=self._on_instruction_loaded,
        )
        self._library_logic.on_generation_state_changed = on_generation_state_changed
        self._instruction_panel.set_callbacks(
            on_clear_instruction_details=self._instruction_details_logic.clear_display,
        )
        self._instruction_details_logic.on_view_changed = self._instruction_details_panel.update_view
        self._instruction_details_logic.on_instruction_changed = self._instruction_panel.display_instruction
        self._instruction_details_panel.on_instruction_parameter_changed = (
            self._instruction_details_logic.handle_instruction_parameter_changed
        )

    def _request_generate_library(self) -> None:
        if self._library_logic.library_available_for_config():
            self._dialogs.show_confirmation(
                TAG_INSTRUCTIONS_LIBRARY_DIALOG_REGENERATE_CONFIRMATION,
                self._msg_regenerate_confirmation,
                self._ttl_regenerate_confirmation,
                self._library_logic.request_generation,
                ok_label=self._lbl_regenerate_confirmation_ok,
            )
            return

        self._library_logic.request_generation()

    def _on_generator_selected(
        self,
        library_key: InstructionLibraryKey,
        generator_name: LibraryGeneratorName,
    ) -> None:
        self._library_logic.load_library_and_set_current(library_key)
        self._library_logic.load_generator(generator_name)

    def _on_generation_completed(self) -> None:
        if not self._is_converter_visible():
            self._dialogs.show_info(
                TAG_INSTRUCTIONS_LIBRARY_PANEL,
                self._msg_generation_success,
                self._ttl_generation_status,
            )

    def _on_generation_error(self, exception: Exception) -> None:
        self._dialogs.show_error(exception, self._msg_generation_failed)

    def _on_generation_cancelled(self) -> None:
        self._dialogs.show_info(
            TAG_INSTRUCTIONS_LIBRARY_PANEL,
            self._msg_generation_cancelled,
            self._ttl_generation_status,
        )

    def _on_library_file_not_found(self, path: Path, message: str) -> None:
        FrameCallbackManager.set_frame_callback(lambda: self._dialogs.show_file_not_found(path, message))

    def _on_library_load_error(self, exception: Exception, message: str) -> None:
        FrameCallbackManager.set_frame_callback(lambda: self._dialogs.show_error(exception, message))

    def _on_instruction_loaded(self, instruction_data: InstructionPanelData) -> None:
        try:
            self._instruction_panel.display_instruction(instruction_data)
            self._instruction_details_logic.display_instruction(instruction_data)
        except LibraryDisplayError as exception:
            self._dialogs.show_error(exception, self._msg_display_error)

        self._on_audio_state_changed()

    def create_tab(self) -> None:
        with dpg.tab(
            tag=TAG_GLOBAL_TAB_INSTRUCTIONS,
            parent=TAG_GLOBAL_TABS,
            label=self._tab_label,
        ):
            with dpg.table(
                parent=TAG_GLOBAL_TAB_INSTRUCTIONS,
                header_row=False,
                resizable=False,
                policy=dpg.mvTable_SizingStretchProp,
            ):
                dpg.add_table_column(width_fixed=True)
                dpg.add_table_column()
                dpg.add_table_column(width_fixed=True)

                with dpg.table_row():
                    with dpg.child_window(
                        tag=f"{TAG_GLOBAL_TAB_INSTRUCTIONS}{SUF_PANEL_LEFT}",
                        width=self._left_width,
                        height=self._left_height,
                        no_scrollbar=True,
                        no_scroll_with_mouse=True,
                    ):
                        self._library_panel.create_panel()
                        self._library_logic.refresh_libraries(load_if_needed=False)

                    with dpg.child_window(
                        tag=f"{TAG_GLOBAL_TAB_INSTRUCTIONS}{SUF_PANEL_CENTER}",
                        no_scroll_with_mouse=True,
                    ):
                        self._instruction_panel.create_panel()

                    with dpg.child_window(
                        tag=f"{TAG_GLOBAL_TAB_INSTRUCTIONS}{SUF_PANEL_RIGHT}",
                        width=self._details_width,
                        height=self._right_height,
                        no_scrollbar=True,
                        no_scroll_with_mouse=True,
                    ):
                        self._instruction_details_panel.create_panel()

    def ensure_library_loaded(self) -> None:
        """Make sure a library matching the current configuration exists before reconstructing.

        The reconstruction pipeline loads the library from disk by the configuration's key, so the
        only requirement here is that the corresponding file is present; it is generated when missing.
        The library's stored parameters are deliberately not applied back to the configuration, which
        would overwrite the user's current settings.
        """
        if not self._library_manager.is_library_available_for_config():
            self._library_logic.generate_library()

    def load_library_file(self, filepath: Path) -> None:
        self._instruction_panel.close_instruction()
        self._library_logic.load_library_file(filepath)

    def close_instruction(self) -> None:
        self._instruction_panel.close_instruction()

    def is_library_generating(self) -> bool:
        return self._library_logic.is_library_generating()

    def refresh_generate_button(self) -> None:
        self._library_panel.refresh_action_buttons()

    @property
    def player_panel(self) -> AudioPlayerPanelProtocol:
        return self._instruction_panel.player_panel
