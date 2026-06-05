from pathlib import Path
from typing import Callable, Optional

import dearpygui.dearpygui as dpg

from sampletones_application.categories.elements.global_ import MenuElements
from sampletones_application.categories.hierarchy import Page, Panel, TextType
from sampletones_application.categories.manager import LanguageManager
from sampletones_application.config.application.manager import SessionManager
from sampletones_application.config.manager import ConfigManager
from sampletones_application.constants.general import (
    SUF_PANEL_CENTER,
    SUF_PANEL_LEFT,
    SUF_PANEL_RIGHT,
    TAG_GLOBAL_TAB_SEQUENCER,
    TAG_GLOBAL_TABS,
)
from sampletones_application.layout.config import LayoutConfig
from sampletones_application.logic.project.controller import ProjectController
from sampletones_application.logic.reconstruction.browser_manager import BrowserManager
from sampletones_application.logic.sequencer.browser import SequencerBrowserLogic
from sampletones_application.logic.sequencer.grid import SequencerGridLogic
from sampletones_application.logic.sequencer.samples import SequencerSamplesLogic
from sampletones_application.logic.shared.player import PlayerLogic
from sampletones_application.ui.panels.sequencer.browser import GUISequencerBrowserPanel
from sampletones_application.ui.panels.sequencer.grid import GUISequencerGridPanel
from sampletones_application.ui.panels.sequencer.samples import GUISequencerSamplesPanel
from sampletones_application.utils.dialogs import DialogsRenderer
from sampletones_application.utils.shortcuts.manager import ShortcutManager
from sampletones_core.audio import AudioDeviceManager
from sampletones_shared.logger import logger


class SequencerTabCoordinator:
    def __init__(
        self,
        config_manager: ConfigManager,
        session_manager: SessionManager,
        audio_device_manager: AudioDeviceManager,
        shortcut_manager: ShortcutManager,
        browser_manager: BrowserManager,
        project_controller: ProjectController,
        *,
        layout: LayoutConfig,
        language_manager: LanguageManager,
        dialogs: DialogsRenderer,
    ) -> None:
        self._project_controller = project_controller
        self.on_edit_sample_requested: Optional[Callable[[str], None]] = None

        self._tab_label = language_manager[
            Page.GLOBAL,
            Panel.MENU,
            TextType.LABEL,
            MenuElements.TAB_SEQUENCER,
        ]
        self._left_width = layout.general.panels.left.width
        self._left_height = layout.general.panels.left.height
        self._instruments_width = layout.sequencer.instruments_panel_width
        self._right_height = layout.general.panels.right.height

        self._sequencer_browser_logic: SequencerBrowserLogic = SequencerBrowserLogic(
            config_manager,
            browser_manager,
            project_controller,
        )
        self._sequencer_browser_panel: GUISequencerBrowserPanel = GUISequencerBrowserPanel(
            self._sequencer_browser_logic,
            session_manager,
            audio_device_manager,
            shortcut_manager,
            scheduling=layout.behavior.scheduling,
            tree_behavior=layout.behavior.sequencer,
            language_manager=language_manager,
            favorite_color=layout.general.colors.favorites.default,
            node_color=layout.general.colors.paths.hover,
        )
        self._sequencer_grid_logic: SequencerGridLogic = SequencerGridLogic(project_controller)
        self._sequencer_samples_logic: SequencerSamplesLogic = SequencerSamplesLogic(project_controller)
        self._sequencer_player_logic = PlayerLogic(audio_device_manager)
        self._sequencer_grid_panel: GUISequencerGridPanel = GUISequencerGridPanel(
            self._sequencer_grid_logic,
            self._sequencer_player_logic,
            layout=layout.sequencer,
            layout_player=layout.player,
            input_width=layout.general.inputs.default_width,
            language_manager=language_manager,
            dialogs=dialogs,
        )
        self._sequencer_samples_panel: GUISequencerSamplesPanel = GUISequencerSamplesPanel(
            layout=layout.sequencer,
            language_manager=language_manager,
        )

        self._wire_callbacks()

    def _wire_callbacks(self) -> None:
        self._sequencer_grid_panel.on_change_rate = self._sequencer_grid_logic.set_change_rate
        self._sequencer_grid_panel.on_tempo = self._sequencer_grid_logic.set_tempo
        self._sequencer_grid_panel.on_speed = self._sequencer_grid_logic.set_speed
        self._sequencer_grid_logic.on_settings_changed = self._sequencer_grid_panel.update_settings
        self._sequencer_grid_logic.on_grid_changed = self._sequencer_grid_panel.update_grid

        self._sequencer_samples_logic.on_samples_changed = self._sequencer_samples_panel.update_view
        self._sequencer_samples_logic.on_edit_sample_requested = self._dispatch_edit_sample
        self._sequencer_samples_panel.on_sample_selected = self._on_sample_selected
        self._sequencer_samples_panel.on_sample_edit_requested = self._sequencer_samples_logic.request_edit
        self._sequencer_browser_panel.on_add_to_sequencer = self._import_reconstruction

        self._project_controller.on_settings_changed = self._sequencer_grid_logic.push_settings
        self._project_controller.on_song_changed = self._sequencer_grid_logic.push_grid
        self._project_controller.on_samples_changed = self._sequencer_samples_logic.push_samples
        self._project_controller.on_project_replaced = self.refresh

    def initialize(self) -> None:
        """Pushes the current project into every sequencer panel.

        Called once after the GUI is built so the panels reflect the project the
        application started with (or restored).
        """
        self.refresh()

    def refresh(self) -> None:
        self._sequencer_grid_logic.refresh()
        self._sequencer_samples_logic.push_samples()

    def _import_reconstruction(self, filepath: Path) -> None:
        self._sequencer_browser_logic.import_reconstruction(filepath)

    def _dispatch_edit_sample(self, sample_id: str) -> None:
        if self.on_edit_sample_requested is not None:
            self.on_edit_sample_requested(sample_id)

    def _on_sample_selected(self, sample_id: str) -> None:
        logger.debug(f"Sequencer sample selected: {sample_id}")

    def create_tab(self) -> None:
        with dpg.tab(
            tag=TAG_GLOBAL_TAB_SEQUENCER,
            parent=TAG_GLOBAL_TABS,
            label=self._tab_label,
        ):
            with dpg.table(
                parent=TAG_GLOBAL_TAB_SEQUENCER,
                header_row=False,
                resizable=False,
                policy=dpg.mvTable_SizingStretchProp,
            ):
                dpg.add_table_column(width_fixed=True)
                dpg.add_table_column()
                dpg.add_table_column(width_fixed=True)

                with dpg.table_row():
                    with dpg.child_window(
                        tag=f"{TAG_GLOBAL_TAB_SEQUENCER}{SUF_PANEL_LEFT}",
                        width=self._left_width,
                        height=self._left_height,
                        no_scrollbar=True,
                        no_scroll_with_mouse=True,
                    ):
                        self._sequencer_browser_panel.create_panel()

                    with dpg.child_window(
                        tag=f"{TAG_GLOBAL_TAB_SEQUENCER}{SUF_PANEL_CENTER}",
                        no_scroll_with_mouse=True,
                    ):
                        self._sequencer_grid_panel.create_panel()

                    with dpg.child_window(
                        tag=f"{TAG_GLOBAL_TAB_SEQUENCER}{SUF_PANEL_RIGHT}",
                        width=self._instruments_width,
                        height=self._right_height,
                        no_scrollbar=True,
                        no_scroll_with_mouse=True,
                    ):
                        self._sequencer_samples_panel.create_panel()
