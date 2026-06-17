from pathlib import Path
from typing import Callable, Optional

import dearpygui.dearpygui as dpg

from sampletones_application.categories.elements.global_ import MenuElements
from sampletones_application.categories.hierarchy import Page, Panel, TextType
from sampletones_application.categories.manager import LanguageManager
from sampletones_application.config.managers.config import ConfigManager
from sampletones_application.config.managers.session import SessionManager
from sampletones_application.constants.general import (
    SUF_PANEL_CENTER,
    SUF_PANEL_LEFT,
    SUF_PANEL_RIGHT,
    TAG_GLOBAL_TAB_SEQUENCER,
    TAG_GLOBAL_TABS,
)
from sampletones_application.constants.sequencer import (
    TAG_SEQUENCER_GRID_PANEL,
    TAG_SEQUENCER_GRID_PANEL_PLAYER,
)
from sampletones_application.coordinators.playback import AudioPlayerPanelProtocol
from sampletones_application.layout.config import LayoutConfig
from sampletones_application.logic.project.controller import ProjectController
from sampletones_application.logic.reconstruction.browser_manager import BrowserManager
from sampletones_application.logic.sequencer.browser import SequencerBrowserLogic
from sampletones_application.logic.sequencer.grid import SequencerGridLogic
from sampletones_application.logic.sequencer.order import SequencerOrderLogic
from sampletones_application.logic.sequencer.playback.song_player import SongPlayerLogic
from sampletones_application.logic.sequencer.samples import SequencerSamplesLogic
from sampletones_application.ui.panels.sequencer.browser import GUISequencerBrowserPanel
from sampletones_application.ui.panels.sequencer.grid import GUISequencerGridPanel
from sampletones_application.ui.panels.sequencer.input.subcolumn import SubColumn
from sampletones_application.ui.panels.sequencer.module import GUISequencerModulePanel
from sampletones_application.ui.panels.sequencer.order import GUISequencerOrderPanel
from sampletones_application.ui.panels.sequencer.samples import GUISequencerSamplesPanel
from sampletones_application.ui.panels.sequencer.song_player import GUISongPlayerPanel
from sampletones_application.utils.dialogs import DialogsRenderer
from sampletones_application.utils.shortcuts.manager import ShortcutManager
from sampletones_application.view_model.sequencer.samples import SequencerSamplesViewModel
from sampletones_application.view_model.sequencer.song_player import SongPlayerViewModel
from sampletones_core.audio import AudioDeviceManager
from sampletones_core.constants.enums import GeneratorName
from sampletones_core.project.instruments.instrument import Instrument
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
        on_edit_sample_requested: Callable[[str], None],
    ) -> None:
        self._project_controller = project_controller
        self._on_edit_sample_requested = on_edit_sample_requested
        self._layout = layout
        self._language_manager = language_manager
        self._dialogs = dialogs

        self._tab_label = language_manager[
            Page.GLOBAL,
            Panel.MENU,
            TextType.LABEL,
            MenuElements.TAB_SEQUENCER,
        ]
        self._left_width = layout.general.panels.left.width
        self._left_height = layout.general.panels.left.height
        self._instruments_width = layout.sequencer.samples_panel_width
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
        self._sequencer_order_logic: SequencerOrderLogic = SequencerOrderLogic(project_controller)
        self._sequencer_samples_logic: SequencerSamplesLogic = SequencerSamplesLogic(project_controller)
        self._song_player_logic: SongPlayerLogic = SongPlayerLogic(
            audio_device_manager,
            project_controller,
            config_manager.config,
        )
        self._player_panel: GUISongPlayerPanel
        self._sequencer_grid_panel: GUISequencerGridPanel = GUISequencerGridPanel(
            layout=layout.sequencer,
            language_manager=language_manager,
        )
        self._sequencer_module_panel: GUISequencerModulePanel = GUISequencerModulePanel(
            self._sequencer_grid_logic,
            layout=layout.sequencer,
            input_width=layout.general.inputs.default_width,
            language_manager=language_manager,
        )
        self._sequencer_order_panel: GUISequencerOrderPanel = GUISequencerOrderPanel(
            layout=layout.sequencer,
            language_manager=language_manager,
        )
        self._sequencer_samples_panel: GUISequencerSamplesPanel = GUISequencerSamplesPanel(
            layout=layout.sequencer,
            language_manager=language_manager,
        )

        self._wire_callbacks()

    def _wire_callbacks(self) -> None:
        self._sequencer_module_panel.on_change_rate = self._sequencer_grid_logic.set_change_rate
        self._sequencer_module_panel.on_rows_per_pattern = self._sequencer_grid_logic.set_rows_per_pattern
        self._sequencer_module_panel.on_tempo = self._sequencer_grid_logic.set_tempo
        self._sequencer_module_panel.on_speed = self._sequencer_grid_logic.set_speed
        self._sequencer_grid_panel.on_clear_row = self._on_clear_row
        self._sequencer_grid_panel.on_clear_subcolumn = self._on_clear_subcolumn
        self._sequencer_grid_panel.on_set_row = self._on_set_row
        self._sequencer_grid_panel.on_cell_selected = self._on_tracker_cell_focused
        self._sequencer_grid_logic.on_settings_changed = self._sequencer_module_panel.update_settings
        self._sequencer_grid_logic.on_grid_changed = self._sequencer_grid_panel.update_grid
        self._sequencer_grid_logic.on_frame_changed = self._sequencer_order_panel.select_position

        self._sequencer_order_logic.on_order_changed = self._sequencer_order_panel.update_order
        self._sequencer_order_panel.on_frame_selected = self._sequencer_grid_logic.select_frame
        self._sequencer_order_panel.on_add_requested = self._on_add_to_order
        self._sequencer_order_panel.on_remove_requested = self._sequencer_order_logic.remove_from_order
        self._sequencer_order_panel.on_set_order_entry = self._sequencer_order_logic.set_order_entry
        self._sequencer_order_panel.on_set_master_entry = self._sequencer_order_logic.set_master_entry
        self._sequencer_order_panel.on_cell_selected = self._sequencer_grid_panel.deselect_cell

        self._sequencer_samples_logic.on_samples_changed = self._on_samples_changed
        self._sequencer_samples_logic.on_edit_sample_requested = self._dispatch_edit_sample
        self._sequencer_samples_panel.on_sample_selected = self._on_sample_selected
        self._sequencer_samples_panel.on_sample_edit_requested = self._sequencer_samples_logic.request_edit
        self._sequencer_samples_panel.on_loop_changed = self._sequencer_samples_logic.set_sample_loop
        self._sequencer_browser_panel.on_add_to_sequencer = self._import_reconstruction

        self._song_player_logic.on_position_changed = self._on_player_position_changed

        self._project_controller.on_settings_changed = self._sequencer_grid_logic.push_settings
        self._project_controller.on_song_changed = self._on_song_changed
        self._project_controller.on_samples_changed = self._sequencer_samples_logic.push_samples
        self._project_controller.on_project_replaced = self.refresh

    def initialize(self) -> None:
        """Pushes the current project into every sequencer panel.

        Called once after the GUI is built so the panels reflect the project the
        application started with (or restored).
        """
        self.refresh()

    def refresh(self) -> None:
        self._song_player_logic.stop()
        self._sequencer_grid_logic.refresh()
        self._sequencer_order_logic.refresh()
        self._sequencer_samples_logic.push_samples()
        is_open = self._project_controller.is_open
        self._sequencer_module_panel.set_enabled(is_open)
        self._sequencer_grid_panel.set_enabled(is_open)
        self._sequencer_order_panel.set_enabled(is_open)

    def _on_song_changed(self) -> None:
        self._sequencer_grid_logic.push_settings()
        self._sequencer_grid_logic.push_grid()
        self._sequencer_order_logic.push_order()

    def _on_player_view_changed(self, view_model: SongPlayerViewModel) -> None:
        if not view_model.is_playing and not view_model.is_paused:
            self._sequencer_grid_panel.set_playing_row(None)
            self._sequencer_order_panel.set_playing_position(None)
        self._player_panel.update_view(view_model)

    def _on_player_position_changed(self, order_position: int, row_index: int) -> None:
        self._sequencer_grid_panel.set_playing_row(row_index)
        self._sequencer_order_panel.set_playing_position(order_position)
        self._sequencer_grid_logic.select_frame(order_position)

    def _import_reconstruction(self, filepath: Path) -> None:
        if not self._project_controller.is_open:
            return

        self._sequencer_browser_logic.import_reconstruction(filepath)

    def _dispatch_edit_sample(self, sample_id: str) -> None:
        self._on_edit_sample_requested(sample_id)

    def _on_clear_row(self, row_index: int, generator: Optional[GeneratorName]) -> None:
        if generator is None:
            self._sequencer_grid_logic.clear_all_generators(row_index)
        else:
            self._sequencer_grid_logic.clear_row(generator, row_index)

    def _on_clear_subcolumn(
        self,
        row_index: int,
        generator: Optional[GeneratorName],
        subcolumn: SubColumn,
    ) -> None:
        instrument = subcolumn is SubColumn.INSTRUMENT
        transpose = subcolumn is SubColumn.TRANSPOSE
        volume = subcolumn is SubColumn.VOLUME
        if generator is None:
            if instrument:
                self._sequencer_grid_logic.clear_subcolumn_all_generators(row_index, instrument=True)
            else:
                self._sequencer_grid_logic.clear_sample_subcolumn(
                    row_index,
                    transpose=transpose,
                    volume=volume,
                )
        else:
            self._sequencer_grid_logic.clear_subcolumn(
                generator,
                row_index,
                instrument=instrument,
                transpose=transpose,
                volume=volume,
            )

    def _on_set_row(
        self,
        row_index: int,
        generator: Optional[GeneratorName],
        sample_id: Optional[str],
        transpose: Optional[int],
        volume: Optional[int],
    ) -> None:
        if generator is None:
            if sample_id is not None:
                self._sequencer_grid_logic.set_sample_instrument(row_index, sample_id)
            elif transpose is not None or volume is not None:
                self._sequencer_grid_logic.set_sample_subcolumn(
                    row_index,
                    transpose=transpose,
                    volume=volume,
                )
        else:
            instrument = (
                Instrument(
                    sample_id=sample_id,
                    generator_name=generator,
                )
                if sample_id is not None
                else None
            )
            self._sequencer_grid_logic.set_row(
                generator,
                row_index,
                instrument=instrument,
                transpose=transpose,
                volume=volume,
            )

    def _on_samples_changed(self, view_model: SequencerSamplesViewModel) -> None:
        self._sequencer_samples_panel.update_view(view_model)
        self._sequencer_grid_panel.update_samples(view_model)

    def _on_sample_selected(self, sample_id: str) -> None:
        logger.debug(f"Sequencer sample selected: {sample_id}")

    def _on_add_to_order(self) -> None:
        empty_position = self._sequencer_order_logic.find_empty_frame(after=self._sequencer_grid_logic.frame_index)
        if empty_position is not None:
            self._sequencer_grid_logic.select_frame(empty_position)
            return

        self._sequencer_order_logic.add_to_order()
        new_position = self._project_controller.order_length - 1
        self._sequencer_grid_logic.select_frame(new_position)

    def _on_tracker_cell_focused(self, row_index: int, generator: Optional[GeneratorName]) -> None:
        """Drops the order's edit cursor when the tracker grid takes focus.

        The two grids share global key handlers; mutually exclusive cursors ensure
        only the focused grid consumes keystrokes (the order's cursor here, the
        tracker's via :meth:`GUISequencerOrderPanel.deselect_cell`).
        """
        self._sequencer_order_panel.deselect_cell()

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
                        self._player_panel = GUISongPlayerPanel(
                            tag=TAG_SEQUENCER_GRID_PANEL_PLAYER,
                            parent=TAG_SEQUENCER_GRID_PANEL,
                            song_player_logic=self._song_player_logic,
                            layout=self._layout.player,
                            language_manager=self._language_manager,
                        )
                        self._song_player_logic.on_view_changed = self._on_player_view_changed
                        self._sequencer_order_panel.create_panel()
                        self._sequencer_grid_panel.create_tracker()

                    with dpg.child_window(
                        tag=f"{TAG_GLOBAL_TAB_SEQUENCER}{SUF_PANEL_RIGHT}",
                        width=self._instruments_width,
                        height=self._right_height,
                        no_scrollbar=True,
                        no_scroll_with_mouse=True,
                    ):
                        self._sequencer_module_panel.create_panel()
                        self._sequencer_samples_panel.create_panel()

    @property
    def player_panel(self) -> AudioPlayerPanelProtocol:
        return self._player_panel
