from pathlib import Path
from typing import Callable, Final, Optional

import dearpygui.dearpygui as dpg

from sampletones_application.categories.elements.global_ import (
    DialogElements,
    MenuElements,
    PlayerElements,
)
from sampletones_application.categories.elements.instructions import (
    InstructionsLibraryElements,
)
from sampletones_application.categories.hierarchy import Page, Panel, TextType
from sampletones_application.categories.manager import LanguageManager
from sampletones_application.config.managers.config import ConfigManager
from sampletones_application.config.managers.session import SessionManager
from sampletones_application.coordinators.playback import (
    AudioPlayerProtocol,
    GuardedPlayer,
)
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
from sampletones_application.tags.general import (
    SUF_PANEL_CENTER,
    SUF_PANEL_LEFT,
    SUF_PANEL_RIGHT,
    TAG_GLOBAL_TAB_INSTRUCTIONS,
    TAG_GLOBAL_TABS,
    TAG_GLOBAL_THEME_PANEL_GROUND,
    TAG_GLOBAL_THEME_PANEL_SURFACE,
)
from sampletones_application.tags.instructions import (
    TAG_INSTRUCTIONS_DETAILS_PANEL,
    TAG_INSTRUCTIONS_DETAILS_WINDOW_PARAMETERS_CARD,
    TAG_INSTRUCTIONS_INSTRUCTION_PANEL_SPECTRUM,
    TAG_INSTRUCTIONS_INSTRUCTION_PANEL_WAVEFORM,
    TAG_INSTRUCTIONS_LIBRARY_DIALOG_REGENERATE_CONFIRMATION,
    TAG_INSTRUCTIONS_LIBRARY_DIALOG_REMOVE_LIBRARY_CONFIRMATION,
    TAG_INSTRUCTIONS_LIBRARY_PANEL,
)
from sampletones_application.ui.elements.layout.columns import ColumnSpec, TabColumns
from sampletones_application.ui.elements.layout.responsive import expanded_side_width
from sampletones_application.ui.elements.status import GUIStatusBar
from sampletones_application.ui.elements.tree.colors import TreeColors
from sampletones_application.ui.panels.instruction.choice import (
    GUIInstructionChoicePanel,
)
from sampletones_application.ui.panels.instruction.library import (
    GUIInstructionsLibraryPanel,
)
from sampletones_application.ui.panels.instruction.parameters import (
    GUIInstructionParametersPanel,
)
from sampletones_application.ui.panels.instruction.spectrum import (
    GUIInstructionSpectrumPanel,
)
from sampletones_application.ui.panels.instruction.waveform import (
    GUIInstructionWaveformPanel,
)
from sampletones_application.utils.gui.dialogs import DialogsRenderer
from sampletones_application.utils.gui.dpg import dpg_configure_item
from sampletones_application.utils.gui.frame import FrameCallbackManager
from sampletones_application.utils.gui.shortcuts.manager import ShortcutManager
from sampletones_application.view_model.instruction.data import InstructionPanelData
from sampletones_application.view_model.instruction.details import (
    InstructionDetailsPanelViewModel,
)
from sampletones_application.view_model.shared.audio_data import AudioData
from sampletones_core.audio import AudioDeviceManager
from sampletones_core.constants.enums import LibraryGeneratorName
from sampletones_core.library import InstructionLibraryKey
from sampletones_shared.exceptions import LibraryDisplayError, SampleToNESError
from sampletones_shared.logger import logger
from sampletones_shared.types.callback import VoidCallback

_LEFT_COLUMN_TAG = f"{TAG_GLOBAL_TAB_INSTRUCTIONS}{SUF_PANEL_LEFT}"
_CENTER_COLUMN_TAG = f"{TAG_GLOBAL_TAB_INSTRUCTIONS}{SUF_PANEL_CENTER}"
_RIGHT_COLUMN_TAG = f"{TAG_GLOBAL_TAB_INSTRUCTIONS}{SUF_PANEL_RIGHT}"
_SIDE_PANEL_COUNT: Final[int] = 2


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
        status_bar: GUIStatusBar,
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
        self._left_width = layout.general.columns.side.width
        self._left_height = layout.general.columns.side.height
        self._details_width = layout.general.columns.instructions_right.width
        self._right_height = layout.general.columns.instructions_right.height
        self._panel_gap = layout.general.panel_gap
        self._rail_width = layout.general.collapse.rail_width
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
        self._ttl_remove_library = language_manager[
            Page.INSTRUCTIONS,
            Panel.LIBRARY,
            TextType.TITLE,
            InstructionsLibraryElements.REMOVE_LIBRARY_DIALOG,
        ]
        self._msg_remove_library = language_manager[
            Page.INSTRUCTIONS,
            Panel.LIBRARY,
            TextType.MESSAGE,
            InstructionsLibraryElements.REMOVE_LIBRARY_MESSAGE,
        ]
        self._lbl_remove = language_manager[
            Page.GLOBAL,
            Panel.DIALOG,
            TextType.LABEL,
            DialogElements.REMOVE,
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
            scheduling=layout.behavior.scheduling,
            initial_collapsed=session_manager.is_card_collapsed(TAG_INSTRUCTIONS_LIBRARY_PANEL),
            language_manager=language_manager,
            status_bar=status_bar,
            colors=TreeColors.create(
                layout.general.colors,
                accent=layout.general.colors.headers.library,
            ),
            is_operation_active=is_operation_active,
        )
        self._library_panel.set_collapse_handler(self._on_library_collapse_changed)
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
        self._library_panel.on_library_remove_requested = self._request_remove_library
        self._instruction_player_logic = PlayerLogic(
            audio_device_manager,
            on_audio_state_changed,
        )
        self._guarded_player = GuardedPlayer(
            self._instruction_player_logic,
            dialogs=dialogs,
            error_message=language_manager[
                Page.GLOBAL,
                Panel.PLAYER,
                TextType.MESSAGE,
                PlayerElements.AUDIO_PLAYBACK_ERROR,
            ],
        )
        self._waveform_panel = GUIInstructionWaveformPanel(
            initial_collapsed=session_manager.is_card_collapsed(TAG_INSTRUCTIONS_INSTRUCTION_PANEL_WAVEFORM),
            layout=layout.graphs,
            language_manager=language_manager,
            status_bar=status_bar,
        )
        self._spectrum_panel = GUIInstructionSpectrumPanel(
            initial_collapsed=session_manager.is_card_collapsed(TAG_INSTRUCTIONS_INSTRUCTION_PANEL_SPECTRUM),
            layout=layout.graphs,
            language_manager=language_manager,
            status_bar=status_bar,
        )
        self._waveform_panel.set_collapse_handler(self._on_card_collapse_changed)
        self._spectrum_panel.set_collapse_handler(self._on_card_collapse_changed)
        self._instruction_player_logic.on_position_changed = self._waveform_panel.set_position
        self._instruction_details_logic = InstructionDetailsPanelLogic(
            library_manager,
            layout=layout.instructions,
            language_manager=language_manager,
        )
        self._instruction_choice_panel = GUIInstructionChoicePanel(
            shortcut_manager,
            layout=layout.instructions,
            general_layout=layout.general,
            initial_collapsed=session_manager.is_card_collapsed(TAG_INSTRUCTIONS_DETAILS_PANEL),
            language_manager=language_manager,
            status_bar=status_bar,
        )
        self._instruction_parameters_panel = GUIInstructionParametersPanel(
            table_colors=layout.general.colors.tables,
            table_layout=layout.general.tables,
            initial_collapsed=session_manager.is_card_collapsed(TAG_INSTRUCTIONS_DETAILS_WINDOW_PARAMETERS_CARD),
            language_manager=language_manager,
        )
        self._instruction_choice_panel.set_collapse_handler(self._on_card_collapse_changed)
        self._instruction_parameters_panel.set_collapse_handler(self._on_card_collapse_changed)

        config_manager.add_config_change_callback(self._library_logic.update_status)

        self._library_logic.set_callbacks(
            on_apply_library_config=config_manager.apply_library_config,
            on_instruction_loaded=self._on_instruction_loaded,
        )
        self._library_logic.on_generation_state_changed = on_generation_state_changed
        self._instruction_details_logic.on_view_changed = self._update_details_view
        self._instruction_details_logic.on_instruction_changed = self._display_instruction
        self._instruction_choice_panel.on_instruction_parameter_changed = (
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

    def _request_remove_library(self, library_key: InstructionLibraryKey) -> None:
        library_path = self._library_logic.get_path(library_key)
        self._dialogs.show_confirmation(
            tag=TAG_INSTRUCTIONS_LIBRARY_DIALOG_REMOVE_LIBRARY_CONFIRMATION,
            title=self._ttl_remove_library,
            message=self._msg_remove_library,
            on_confirm=lambda: self._remove_library(library_key),
            ok_label=self._lbl_remove,
            path=library_path,
        )

    def _remove_library(self, library_key: InstructionLibraryKey) -> None:
        displayed_instruction = self._instruction_details_logic.get_current_instruction_data()
        was_displaying_removed_library = (
            displayed_instruction is not None and displayed_instruction.library_key == library_key
        )
        try:
            self._library_logic.remove_library(library_key)
        except (OSError, SampleToNESError) as exception:
            logger.error_with_traceback(exception, f"Failed to remove library: {library_key}")
            self._dialogs.show_error(exception)
            return

        if was_displaying_removed_library:
            self._close_instruction()
            self._on_audio_state_changed()

    def _on_generation_completed(self) -> None:
        if not self._is_converter_visible():
            self._dialogs.show_info(
                TAG_INSTRUCTIONS_LIBRARY_PANEL,
                self._msg_generation_success,
                self._ttl_generation_status,
                modal=True,
            )

    def _on_generation_error(self, exception: Exception) -> None:
        self._dialogs.show_error(exception, self._msg_generation_failed)

    def _on_generation_cancelled(self) -> None:
        self._dialogs.show_info(
            TAG_INSTRUCTIONS_LIBRARY_PANEL,
            self._msg_generation_cancelled,
            self._ttl_generation_status,
            modal=True,
        )

    def _on_library_file_not_found(self, path: Path, message: str) -> None:
        FrameCallbackManager.set_frame_callback(lambda: self._dialogs.show_file_not_found(path, message))

    def _on_library_load_error(self, exception: Exception, message: str) -> None:
        FrameCallbackManager.set_frame_callback(lambda: self._dialogs.show_error(exception, message))

    def _display_instruction(self, instruction_data: Optional[InstructionPanelData]) -> None:
        """Renders the instruction and reloads the player with its audio.

        Both entry points — a fresh load from the library and a parameter edit
        from the details panel — route here, so the audible fragment always
        matches the displayed one. An empty selection clears the displays and
        leaves the player untouched.
        """
        if instruction_data is None:
            self._close_instruction()
            return

        self._render_instruction(instruction_data)
        self._instruction_player_logic.load_audio_data(
            AudioData.from_library_fragment(
                instruction_data.fragment,
                instruction_data.config.sample_rate,
            )
        )

    def _render_instruction(self, instruction_data: InstructionPanelData) -> None:
        """Loads the fragment into the waveform and spectrum displays.

        A data-shape failure that leaves the fragment unplottable is reclassified as a
        ``LibraryDisplayError`` so the recovery boundary in ``_on_instruction_loaded``
        turns it into a display-error dialog.
        """
        config = instruction_data.config
        fragment = instruction_data.fragment

        try:
            self._waveform_panel.load_library_fragment(fragment)
            self._spectrum_panel.load_library_fragment(
                fragment,
                config.sample_rate,
                config.window_size,
            )
        except (KeyError, IndexError, ValueError) as exception:
            logger.error_with_traceback(exception, "Error while plotting library data")
            raise LibraryDisplayError("Could not display library data") from exception

    def _close_instruction(self) -> None:
        """Clears the waveform and spectrum displays and the instruction details."""
        self._waveform_panel.clear_layers()
        self._spectrum_panel.clear_layers()
        self._instruction_details_logic.clear_display()
        self._instruction_player_logic.clear_audio()

    def _on_card_collapse_changed(self, card_tag: str, collapsed: bool) -> None:
        """Persists a centre-column card's collapsed state so it restores on the next launch."""
        self._session_manager.set_card_collapsed(card_tag, collapsed)

    def _on_library_collapse_changed(self, card_tag: str, collapsed: bool) -> None:
        """Persists the library panel's collapse, then docks or restores the width of the column it fills."""
        self._session_manager.set_card_collapsed(card_tag, collapsed)
        self._sync_library_width()

    def sync_column_widths(self) -> None:
        """Refits this tab's side column to the current viewport, the entry the resize handler calls."""
        self._sync_library_width()

    def _sync_library_width(self) -> None:
        """Shrinks the library column to the collapse rail when collapsed, else sizes it to the viewport width."""
        if self._library_panel.collapsed:
            width = self._rail_width
        else:
            width = expanded_side_width(self._left_width, dpg.get_viewport_client_width(), _SIDE_PANEL_COUNT)
        dpg_configure_item(_LEFT_COLUMN_TAG, width=width)

    def _update_details_view(self, view_model: InstructionDetailsPanelViewModel) -> None:
        """Fans the details view model out to the parameters and choice cards."""
        self._instruction_parameters_panel.update_tables(view_model.table_data)
        self._instruction_choice_panel.update_choice(view_model.instruction_data)

    def _on_instruction_loaded(self, instruction_data: InstructionPanelData) -> None:
        try:
            self._display_instruction(instruction_data)
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
            TabColumns.build(
                panel_gap=self._panel_gap,
                columns=[
                    ColumnSpec(
                        tag=_LEFT_COLUMN_TAG,
                        build=self._library_panel.create_panel,
                        theme=TAG_GLOBAL_THEME_PANEL_SURFACE,
                        width=self._left_width,
                        height=self._left_height,
                        no_scrollbar=True,
                    ),
                    ColumnSpec(
                        tag=_CENTER_COLUMN_TAG,
                        build=self._build_display_column,
                        theme=TAG_GLOBAL_THEME_PANEL_GROUND,
                        border=False,
                    ),
                    ColumnSpec(
                        tag=_RIGHT_COLUMN_TAG,
                        build=self._build_details_column,
                        theme=TAG_GLOBAL_THEME_PANEL_GROUND,
                        width=self._details_width,
                        height=self._right_height,
                        border=False,
                        no_scrollbar=True,
                    ),
                ],
            )

        self._sync_library_width()

    def _build_display_column(self, parent: str) -> None:
        """Stacks the waveform and spectrum cards down the centre column."""
        self._waveform_panel.create_panel(parent)
        dpg.add_spacer(height=self._panel_gap, parent=parent)
        self._spectrum_panel.create_panel(parent)

    def _build_details_column(self, parent: str) -> None:
        """Stacks the instruction-choice and parameters cards down the right column."""
        self._instruction_choice_panel.create_panel(parent)
        dpg.add_spacer(height=self._panel_gap, parent=parent)
        self._instruction_parameters_panel.create_panel(parent)

    def initialize(self) -> None:
        """Populates the library tree once the tab's widgets exist."""
        self._library_logic.refresh_libraries(load_if_needed=False)

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
        self._close_instruction()
        self._library_logic.load_library_file(filepath)

    def load_library_safely(self, filepath: Path) -> None:
        try:
            self.load_library_file(filepath)
        except (SampleToNESError, OSError) as exception:
            logger.warning(f"Could not load library from {logger.format_path(filepath)}: {exception}")

    def close_instruction(self) -> None:
        self._close_instruction()

    def is_library_generating(self) -> bool:
        return self._library_logic.is_library_generating()

    def refresh_generate_button(self) -> None:
        self._library_panel.refresh_action_buttons()

    @property
    def player(self) -> AudioPlayerProtocol:
        return self._guarded_player
