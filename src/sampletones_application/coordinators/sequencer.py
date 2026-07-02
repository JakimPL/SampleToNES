from pathlib import Path
from typing import Callable, Optional, ParamSpec

import dearpygui.dearpygui as dpg

from sampletones_application.categories.elements.global_ import (
    DialogElements,
    GlobalDialogTitleElements,
    GlobalMessageElements,
    MenuElements,
)
from sampletones_application.categories.elements.sequencer import SequencerHistoryActionElements
from sampletones_application.categories.hierarchy import Page, Panel, Tab, TextType
from sampletones_application.categories.manager import LanguageManager
from sampletones_application.config.managers.config import ConfigManager
from sampletones_application.config.managers.session import SessionManager
from sampletones_application.constants.general import (
    SUF_PANEL_CENTER,
    SUF_PANEL_LEFT,
    SUF_PANEL_RIGHT,
    TAG_GLOBAL_DIALOG_NO_PROJECT_OPEN,
    TAG_GLOBAL_TAB_SEQUENCER,
    TAG_GLOBAL_TABS,
)
from sampletones_application.constants.sequencer import (
    TAG_SEQUENCER_BROWSER_DIALOG_FREQUENCY,
    TAG_SEQUENCER_GRID_PANEL,
    TAG_SEQUENCER_GRID_PANEL_PLAYER,
    TAG_SEQUENCER_INSTRUMENTS_DIALOG_REMOVE,
    TAG_SEQUENCER_MODULE_DIALOG_NES_FREQUENCY,
)
from sampletones_application.coordinators.playback import AudioPlayerPanelProtocol
from sampletones_application.layout.config import LayoutConfig
from sampletones_application.logic.history.action import HistoryAction
from sampletones_application.logic.history.manager import HistoryManager
from sampletones_application.logic.history.snapshot import HistoryEntry
from sampletones_application.logic.project.controller import ProjectController
from sampletones_application.logic.reconstruction.browser_manager import BrowserManager
from sampletones_application.logic.sequencer.browser import SequencerBrowserLogic
from sampletones_application.logic.sequencer.grid import SequencerGridLogic
from sampletones_application.logic.sequencer.order import SequencerOrderLogic
from sampletones_application.logic.sequencer.playback.playhead import (
    remap_after_insert,
    remap_after_move,
    remap_after_remove,
)
from sampletones_application.logic.sequencer.playback.song_player import SongPlayerLogic
from sampletones_application.logic.sequencer.samples import SequencerSamplesLogic
from sampletones_application.ui.elements.tree.colors import TreeColors
from sampletones_application.ui.panels.sequencer.browser import GUISequencerBrowserPanel
from sampletones_application.ui.panels.sequencer.grid import GUISequencerGridPanel
from sampletones_application.ui.panels.sequencer.history import GUISequencerHistoryPanel
from sampletones_application.ui.panels.sequencer.input.subcolumn import SubColumn
from sampletones_application.ui.panels.sequencer.module import GUISequencerModulePanel
from sampletones_application.ui.panels.sequencer.order import GUISequencerOrderPanel
from sampletones_application.ui.panels.sequencer.samples import GUISequencerSamplesPanel
from sampletones_application.ui.panels.sequencer.song_player import GUISongPlayerPanel
from sampletones_application.utils.gui.dialogs import DialogsRenderer
from sampletones_application.utils.gui.frame import FrameCallbackManager
from sampletones_application.utils.gui.shortcuts.manager import ShortcutManager
from sampletones_application.view_model.sequencer.history import (
    HistoryEntryViewModel,
    HistoryViewModel,
)
from sampletones_application.view_model.sequencer.samples import (
    SequencerSamplesViewModel,
)
from sampletones_application.view_model.sequencer.song_player import SongPlayerViewModel
from sampletones_core.audio import AudioDeviceManager
from sampletones_core.constants.enums import GeneratorName
from sampletones_core.project.instruments.instrument import Instrument
from sampletones_core.reconstructions import Reconstruction
from sampletones_core.utils.display import display_id
from sampletones_shared.exceptions import SampleToNESError
from sampletones_shared.logger import logger

_UndoableParams = ParamSpec("_UndoableParams")


class SequencerTabCoordinator:
    def __init__(
        self,
        config_manager: ConfigManager,
        session_manager: SessionManager,
        audio_device_manager: AudioDeviceManager,
        shortcut_manager: ShortcutManager,
        browser_manager: BrowserManager,
        project_controller: ProjectController,
        history: HistoryManager,
        *,
        layout: LayoutConfig,
        language_manager: LanguageManager,
        dialogs: DialogsRenderer,
        on_edit_sample_requested: Callable[[str], None],
        on_tab_switch: Callable[[Tab], None],
    ) -> None:
        self._project_controller = project_controller
        self._history = history
        self._on_edit_sample_requested = on_edit_sample_requested
        self._on_tab_switch = on_tab_switch
        self._layout = layout
        self._language_manager = language_manager
        self._dialogs = dialogs

        self._tab_label = language_manager[
            Page.GLOBAL,
            Panel.MENU,
            TextType.LABEL,
            MenuElements.TAB_SEQUENCER,
        ]
        self._msg_no_project = language_manager[
            Page.GLOBAL,
            Panel.DIALOG,
            TextType.MESSAGE,
            GlobalMessageElements.NO_PROJECT_OPEN,
        ]
        self._ttl_no_project = language_manager[
            Page.GLOBAL,
            Panel.DIALOG,
            TextType.TITLE,
            GlobalDialogTitleElements.NO_PROJECT_OPEN,
        ]
        self._ttl_remove_sample = language_manager[
            Page.GLOBAL,
            Panel.DIALOG,
            TextType.TITLE,
            GlobalDialogTitleElements.REMOVE_SAMPLE,
        ]
        self._msg_remove_sample = language_manager[
            Page.GLOBAL,
            Panel.DIALOG,
            TextType.MESSAGE,
            GlobalMessageElements.REMOVE_SAMPLE,
        ]
        self._lbl_remove_sample = language_manager[
            Page.GLOBAL,
            Panel.DIALOG,
            TextType.LABEL,
            DialogElements.REMOVE,
        ]
        self._ttl_change_nes_frequency = language_manager[
            Page.GLOBAL,
            Panel.DIALOG,
            TextType.TITLE,
            GlobalDialogTitleElements.CHANGE_NES_FREQUENCY,
        ]
        self._msg_change_nes_frequency = language_manager[
            Page.GLOBAL,
            Panel.DIALOG,
            TextType.MESSAGE,
            GlobalMessageElements.CHANGE_NES_FREQUENCY,
        ]
        self._lbl_change_nes_frequency = language_manager[
            Page.GLOBAL,
            Panel.DIALOG,
            TextType.LABEL,
            DialogElements.CHANGE,
        ]
        self._lbl_dont_ask_again = language_manager[
            Page.GLOBAL,
            Panel.DIALOG,
            TextType.LABEL,
            DialogElements.DONT_ASK_AGAIN,
        ]
        self._ttl_frequency_mismatch = language_manager[
            Page.GLOBAL,
            Panel.DIALOG,
            TextType.TITLE,
            GlobalDialogTitleElements.FREQUENCY_MISMATCH,
        ]
        self._msg_frequency_mismatch = language_manager[
            Page.GLOBAL,
            Panel.DIALOG,
            TextType.MESSAGE,
            GlobalMessageElements.FREQUENCY_MISMATCH,
        ]
        self._lbl_add_anyway = language_manager[
            Page.GLOBAL,
            Panel.DIALOG,
            TextType.LABEL,
            DialogElements.ADD_ANYWAY,
        ]
        self._nes_frequency_change_acknowledged: bool = False
        self._playing_order: Optional[int] = None
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
            colors=TreeColors.create(
                layout.general.colors,
                accent=layout.general.colors.headers.reconstruction,
            ),
        )
        self._sequencer_grid_logic: SequencerGridLogic = SequencerGridLogic(project_controller)
        self._sequencer_order_logic: SequencerOrderLogic = SequencerOrderLogic(project_controller)
        self._sequencer_samples_logic: SequencerSamplesLogic = SequencerSamplesLogic(
            project_controller,
            session_manager,
            audio_device_manager,
            scheduling=layout.behavior.scheduling,
        )
        self._song_player_logic: SongPlayerLogic = SongPlayerLogic(
            audio_device_manager,
            project_controller,
            config_manager.config,
            session_manager,
        )
        self._player_panel: GUISongPlayerPanel
        self._sequencer_grid_panel: GUISequencerGridPanel = GUISequencerGridPanel(
            layout=layout.sequencer,
            language_manager=language_manager,
            shortcut_manager=shortcut_manager,
        )
        self._sequencer_module_panel: GUISequencerModulePanel = GUISequencerModulePanel(
            self._sequencer_grid_logic,
            layout=layout.sequencer,
            input_width=layout.general.inputs.default_width,
            language_manager=language_manager,
            shortcut_manager=shortcut_manager,
        )
        self._sequencer_order_panel: GUISequencerOrderPanel = GUISequencerOrderPanel(
            layout=layout.sequencer,
            language_manager=language_manager,
            shortcut_manager=shortcut_manager,
        )
        self._sequencer_samples_panel: GUISequencerSamplesPanel = GUISequencerSamplesPanel(
            layout=layout.sequencer,
            language_manager=language_manager,
            shortcut_manager=shortcut_manager,
        )
        self._sequencer_history_panel: GUISequencerHistoryPanel = GUISequencerHistoryPanel(
            layout=layout.sequencer,
            language_manager=language_manager,
        )

        self._wire_callbacks()

    def _wire_callbacks(self) -> None:
        self._sequencer_module_panel.on_nes_frequency = self._request_nes_frequency_change
        self._sequencer_module_panel.on_rows_per_pattern = self._undoable(
            HistoryAction.SET_ROWS_PER_PATTERN,
            self._sequencer_grid_logic.set_rows_per_pattern,
            detail=str,
        )
        self._sequencer_module_panel.on_tempo = self._undoable(
            HistoryAction.SET_TEMPO,
            self._sequencer_grid_logic.set_tempo,
            detail=str,
        )
        self._sequencer_module_panel.on_speed = self._undoable(
            HistoryAction.SET_SPEED,
            self._sequencer_grid_logic.set_speed,
            detail=str,
        )
        self._sequencer_grid_panel.on_clear_row = self._undoable(
            HistoryAction.CLEAR_ROW,
            self._on_clear_row,
        )
        self._sequencer_grid_panel.on_clear_subcolumn = self._undoable(
            HistoryAction.CLEAR_SUBCOLUMN,
            self._on_clear_subcolumn,
        )
        self._sequencer_grid_panel.on_set_row = self._undoable(
            HistoryAction.EDIT_ROW,
            self._on_set_row,
            detail=self._edit_row_detail,
        )
        self._sequencer_grid_panel.on_set_note_off = self._undoable(
            HistoryAction.NOTE_OFF,
            self._on_set_note_off,
        )
        self._sequencer_grid_panel.on_cell_selected = self._on_tracker_cell_focused
        self._sequencer_grid_panel.on_play_from_row = self._on_grid_play_from_row
        self._sequencer_grid_panel.on_adjust_transpose = self._undoable(
            HistoryAction.ADJUST_TRANSPOSE, self._on_adjust_transpose
        )
        self._sequencer_grid_panel.on_adjust_volume = self._undoable(
            HistoryAction.ADJUST_VOLUME, self._on_adjust_volume
        )
        self._sequencer_grid_logic.on_settings_changed = self._sequencer_module_panel.update_settings
        self._sequencer_grid_logic.on_grid_changed = self._sequencer_grid_panel.update_grid
        self._sequencer_grid_logic.on_frame_changed = self._sequencer_order_panel.select_position

        self._sequencer_order_logic.on_order_changed = self._sequencer_order_panel.update_order
        self._sequencer_order_panel.on_frame_selected = self._on_order_frame_selected
        self._sequencer_order_panel.on_remove_requested = self._undoable(
            HistoryAction.REMOVE_FRAME, self._on_order_remove
        )
        self._sequencer_order_panel.on_duplicate_requested = self._undoable(
            HistoryAction.DUPLICATE_FRAME, self._on_order_duplicate
        )
        self._sequencer_order_panel.on_insert_requested = self._undoable(HistoryAction.ADD_FRAME, self._on_order_insert)
        self._sequencer_order_panel.on_clear_requested = self._undoable(HistoryAction.CLEAR_FRAME, self._on_order_clear)
        self._sequencer_order_panel.on_play_from_requested = self._on_order_play_from
        self._sequencer_order_panel.on_move_requested = self._undoable(HistoryAction.MOVE_FRAME, self._on_order_move)
        self._sequencer_order_panel.on_set_order_entry = self._undoable(
            HistoryAction.SET_ORDER_ENTRY, self._sequencer_order_logic.set_order_entry
        )
        self._sequencer_order_panel.on_set_master_entry = self._undoable(
            HistoryAction.SET_ORDER_ENTRY, self._sequencer_order_logic.set_master_entry
        )
        self._sequencer_order_panel.on_cell_selected = self._on_order_cell_focused

        self._sequencer_samples_logic.on_samples_changed = self._on_samples_changed
        self._sequencer_samples_logic.on_edit_sample_requested = self._dispatch_edit_sample
        self._sequencer_samples_logic.on_autoplay_error = self._on_preview_error
        self._sequencer_samples_panel.on_sample_selected = self._on_sample_selected
        self._sequencer_samples_panel.on_sample_edit_requested = self._sequencer_samples_logic.request_edit
        self._sequencer_samples_panel.on_loop_changed = self._undoable(
            HistoryAction.SET_SAMPLE_LOOP, self._sequencer_samples_logic.set_sample_loop
        )
        self._sequencer_samples_panel.on_remove_requested = self._remove_sample
        self._sequencer_samples_panel.on_play_requested = self._sequencer_samples_logic.play_sample
        self._sequencer_samples_panel.on_move_requested = self._undoable(
            HistoryAction.MOVE_SAMPLE, self._sequencer_samples_logic.move_sample
        )
        self._sequencer_samples_panel.on_rename_committed = self._submit_rename
        self._sequencer_samples_panel.on_duplicate_requested = self._undoable(
            HistoryAction.DUPLICATE_SAMPLE, self._sequencer_samples_logic.duplicate_sample
        )
        self._sequencer_browser_panel.on_add_to_sequencer = self.import_reconstruction
        self._sequencer_browser_panel.can_add_to_sequencer = self._is_project_open
        self._sequencer_browser_panel.logic.on_autoplay_error = self._on_preview_error

        self._song_player_logic.on_position_changed = self._on_player_position_changed
        self._song_player_logic.on_error = self._on_player_error

        self._project_controller.on_settings_changed = self._sequencer_grid_logic.push_settings
        self._project_controller.on_song_changed = self._on_song_changed
        self._project_controller.on_samples_changed = self._sequencer_samples_logic.push_samples
        self._project_controller.on_project_replaced = self._on_project_replaced
        self._wire_history()

    def _wire_history(self) -> None:
        self._history.on_history_changed = self._on_history_changed
        self._sequencer_history_panel.on_undo = self.undo
        self._sequencer_history_panel.on_redo = self.redo
        self._sequencer_history_panel.on_jump_to = self.jump_to_history

    def _undoable(
        self,
        action: HistoryAction,
        callback: Callable[_UndoableParams, None],
        *,
        detail: Optional[Callable[_UndoableParams, Optional[str]]] = None,
    ) -> Callable[_UndoableParams, None]:
        """Wraps a state-changing hook so its whole gesture becomes one undo entry.

        Every mutation the wrapped callback triggers is grouped under ``action``;
        a gesture that changes nothing records no entry. ``detail`` computes the
        entry's extra description from the same arguments the hook receives.
        """

        def wrapped(*args: _UndoableParams.args, **kwargs: _UndoableParams.kwargs) -> None:
            description = detail(*args, **kwargs) if detail is not None else None
            with self._history.transaction(action, detail=description):
                callback(*args, **kwargs)

        return wrapped

    def _edit_row_detail(
        self,
        row_index: int,
        generator: Optional[GeneratorName],
        sample_id: Optional[str],
        transpose: Optional[int],
        volume: Optional[int],
    ) -> str:
        """Locates the edit as ``<order> [<channel>] <row>[: <sample position>]``.

        Order and row are the hex frame and row indices; the channel name is
        present for a single-channel edit and absent when the whole sample column
        is touched; the sample position is the referenced sample's hex list id.
        """
        order = display_id(self._sequencer_grid_logic.frame_index)
        row = display_id(row_index)
        location = f"{order} {generator.capitalized} {row}" if generator is not None else f"{order} {row}"
        if sample_id is not None:
            return f"{location}: {self._sequencer_samples_logic.sample_position(sample_id)}"
        return location

    def _on_project_replaced(self) -> None:
        self._history.reset()
        self.refresh()

    def undo(self) -> None:
        self._history.undo()

    def redo(self) -> None:
        self._history.redo()

    def jump_to_history(self, index: int) -> None:
        self._history.jump_to(index)

    def _on_history_changed(self) -> None:
        self._sequencer_history_panel.update_view(self._build_history_view_model())

    def _build_history_view_model(self) -> HistoryViewModel:
        cursor = self._history.cursor
        entries = tuple(
            HistoryEntryViewModel(
                index=index,
                text=self._history_entry_text(entry),
                is_current=index == cursor,
                is_future=index > cursor,
            )
            for index, entry in enumerate(self._history.entries)
        )
        return HistoryViewModel(entries=entries, cursor=cursor)

    def _history_entry_text(self, entry: HistoryEntry) -> str:
        label = self._language_manager[
            Page.SEQUENCER,
            Panel.HISTORY,
            TextType.LABEL,
            SequencerHistoryActionElements(entry.action.value),
        ]
        if entry.detail is None:
            return label
        return f"{label}: {entry.detail}"

    def initialize(self) -> None:
        """Pushes the current project into every sequencer panel.

        Called once after the GUI is built so the panels reflect the project the
        application started with (or restored).
        """
        self.refresh()

    def refresh(self) -> None:
        self._nes_frequency_change_acknowledged = False
        self._song_player_logic.stop()
        self._sequencer_grid_logic.refresh()
        self._sequencer_order_logic.refresh()
        self._sequencer_samples_logic.push_samples()
        is_open = self._project_controller.is_open
        self._sequencer_module_panel.set_enabled(is_open)
        self._sequencer_grid_panel.set_enabled(is_open)
        self._sequencer_order_panel.set_enabled(is_open)
        self._sequencer_history_panel.set_enabled(is_open)

    def _on_song_changed(self) -> None:
        self._sequencer_grid_logic.push_settings()
        self._sequencer_grid_logic.push_grid()
        self._sequencer_order_logic.push_order()

    def _on_player_error(self, error: Exception) -> None:
        self._dialogs.show_error(error)

    def _on_player_view_changed(self, view_model: SongPlayerViewModel) -> None:
        if not view_model.is_playing and not view_model.is_paused:
            self._playing_order = None
            self._sequencer_grid_panel.set_playing_row(None)
            self._sequencer_order_panel.set_playing_position(None)

        self._player_panel.update_view(view_model)

    def _on_player_position_changed(self, order_position: int, row_index: int) -> None:
        self._playing_order = order_position
        self._sequencer_grid_panel.set_playing_row(row_index)
        self._sequencer_order_panel.set_playing_position(order_position)
        if self._song_player_logic.follow_playback:
            self._sequencer_grid_logic.select_frame(order_position)

    def _on_order_frame_selected(self, frame_index: int) -> None:
        """Selects an order frame in the grid, and moves the playhead too when following.

        With follow-playback on, choosing another order during playback relocates the playhead to
        it (the seek no-ops when stopped); with it off, the selection only changes which pattern is
        edited, leaving playback where it is.
        """
        self._sequencer_grid_logic.select_frame(frame_index)
        if self._song_player_logic.follow_playback:
            self._song_player_logic.seek(frame_index)

    def _on_preview_error(self, exception: Exception) -> None:
        FrameCallbackManager.set_frame_callback(lambda: self._dialogs.show_error(exception))

    def _is_project_open(self) -> bool:
        return self._project_controller.is_open

    def import_reconstruction(self, filepath: Path) -> None:
        if not self._project_controller.is_open:
            self._dialogs.show_info(
                TAG_GLOBAL_DIALOG_NO_PROJECT_OPEN,
                self._msg_no_project,
                self._ttl_no_project,
            )
            return

        try:
            reconstruction = self._sequencer_browser_logic.load_reconstruction(filepath)
        except (SampleToNESError, OSError, ValueError) as exception:
            logger.error_with_traceback(exception, f"Failed to load reconstruction from {filepath}")
            self._dialogs.show_error(exception)
            return
        except Exception as exception:
            logger.error_with_traceback(exception, f"Unexpected error while loading reconstruction from {filepath}")
            self._dialogs.show_error(exception)
            return

        self._add_reconstruction_with_frequency_check(reconstruction, filepath.stem)

    def import_reconstruction_object(self, reconstruction: Reconstruction, name: str) -> None:
        """Adds an in-memory reconstruction — the one open in the Reconstruction tab — as a sample."""
        if not self._project_controller.is_open:
            self._dialogs.show_info(
                TAG_GLOBAL_DIALOG_NO_PROJECT_OPEN,
                self._msg_no_project,
                self._ttl_no_project,
            )
            return

        self._add_reconstruction_with_frequency_check(reconstruction, name)

    def _add_reconstruction_with_frequency_check(self, reconstruction: Reconstruction, name: str) -> None:
        """Adds a loaded reconstruction, reconciling its NES frequency with the project's.

        A reconstruction is rendered at the frequency it was generated at, so importing one
        recorded at a different rate plays back wrong. An empty project simply adopts the
        incoming frequency; a project that already holds samples (which a frequency change would
        re-time) confirms first, showing both rates.
        """
        reconstruction_frequency = reconstruction.config.nes_frequency
        project_frequency = self._sequencer_grid_logic.settings.nes_frequency

        if reconstruction_frequency == project_frequency:
            self._commit_add_reconstruction(reconstruction, name, adopt_frequency=None)
            return

        if not self._project_controller.has_samples:
            self._commit_add_reconstruction(reconstruction, name, adopt_frequency=reconstruction_frequency)
            return

        self._dialogs.show_confirmation(
            tag=TAG_SEQUENCER_BROWSER_DIALOG_FREQUENCY,
            title=self._ttl_frequency_mismatch,
            message=self._msg_frequency_mismatch.format(
                reconstruction=reconstruction_frequency,
                project=project_frequency,
            ),
            on_confirm=lambda: self._commit_add_reconstruction(
                reconstruction,
                name,
                adopt_frequency=None,
            ),
            ok_label=self._lbl_add_anyway,
        )

    def _commit_add_reconstruction(
        self,
        reconstruction: Reconstruction,
        name: str,
        *,
        adopt_frequency: Optional[int],
    ) -> None:
        """Adds a reconstruction as one undoable gesture, optionally adopting its frequency.

        The frequency reconciliation and the sample insertion form a single history
        entry, so undoing a freshly-imported sample also restores the prior rate.
        """
        with self._history.transaction(HistoryAction.ADD_SAMPLE, detail=name):
            if adopt_frequency is not None:
                self._sequencer_grid_logic.set_nes_frequency(adopt_frequency)
            self._sequencer_browser_logic.add_reconstruction(reconstruction, name)
        self._on_tab_switch(Tab.SEQUENCER)

    def _dispatch_edit_sample(self, sample_id: str) -> None:
        self._on_edit_sample_requested(sample_id)

    def _on_clear_row(
        self,
        row_index: int,
        generator: Optional[GeneratorName],
    ) -> None:
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
                self._sequencer_grid_logic.clear_subcolumn_all_generators(
                    row_index,
                    instrument=True,
                )
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
                self._sequencer_grid_logic.set_sample_instrument(
                    row_index,
                    sample_id,
                )
            elif transpose is not None or volume is not None:
                self._sequencer_grid_logic.set_sample_subcolumn(
                    row_index,
                    transpose=transpose,
                    volume=volume,
                )
        else:
            command = (
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
                command=command,
                transpose=transpose,
                volume=volume,
            )

    def _on_set_note_off(
        self,
        row_index: int,
        generator: Optional[GeneratorName],
    ) -> None:
        """Writes a note-off: to one channel, or across every channel from the sample column."""
        if generator is None:
            self._sequencer_grid_logic.set_note_off_all_generators(row_index)
        else:
            self._sequencer_grid_logic.set_note_off(generator, row_index)

    def _on_grid_play_from_row(self, row_index: int) -> None:
        """Starts playback from the right-clicked row of the frame the grid is showing."""
        self._song_player_logic.play_from(
            self._sequencer_grid_logic.frame_index,
            row_index,
        )

    def _on_adjust_transpose(
        self,
        row_index: int,
        generator: Optional[GeneratorName],
        delta: int,
    ) -> None:
        """Shifts transpose: one channel, or across the sample column's channels."""
        if generator is None:
            self._sequencer_grid_logic.adjust_sample_transpose(row_index, delta)
        else:
            self._sequencer_grid_logic.adjust_transpose(
                generator,
                row_index,
                delta,
            )

    def _on_adjust_volume(
        self,
        row_index: int,
        generator: Optional[GeneratorName],
        delta: int,
    ) -> None:
        """Shifts volume: one channel, or across the sample column's channels."""
        if generator is None:
            self._sequencer_grid_logic.adjust_sample_volume(row_index, delta)
        else:
            self._sequencer_grid_logic.adjust_volume(
                generator,
                row_index,
                delta,
            )

    def _on_samples_changed(
        self,
        view_model: SequencerSamplesViewModel,
    ) -> None:
        self._sequencer_samples_panel.update_view(view_model)
        self._sequencer_grid_panel.update_samples(view_model)

    def _on_sample_selected(self, sample_id: str) -> None:
        self._sequencer_grid_panel.deselect_cell()
        self._sequencer_order_panel.deselect_cell()
        self._sequencer_samples_logic.request_autoplay(sample_id)
        logger.debug(f"Sequencer sample selected: {sample_id}")

    def _remove_sample(self, sample_id: str) -> None:
        """Removes a sample, confirming first only when a pattern still references it.

        An unused sample is dropped silently; a referenced one would clear every row
        that points at it, so the user confirms that loss first.
        """
        if not self._sequencer_samples_logic.is_sample_used(sample_id):
            self._perform_remove_sample(sample_id)
            return

        name = self._sequencer_samples_logic.sample_name(sample_id)
        self._dialogs.show_confirmation(
            tag=TAG_SEQUENCER_INSTRUMENTS_DIALOG_REMOVE,
            title=self._ttl_remove_sample,
            message=self._msg_remove_sample.format(name=name),
            on_confirm=lambda: self._perform_remove_sample(sample_id),
            ok_label=self._lbl_remove_sample,
        )

    def _perform_remove_sample(self, sample_id: str) -> None:
        name = self._sequencer_samples_logic.sample_name(sample_id)
        with self._history.transaction(HistoryAction.REMOVE_SAMPLE, detail=name):
            self._sequencer_samples_logic.remove_sample(sample_id)

    def _submit_rename(self, sample_id: str, name: str) -> None:
        """Applies an inline rename, ignoring a blank name so the sample keeps its current one."""
        stripped = name.strip()
        if stripped:
            with self._history.transaction(HistoryAction.RENAME_SAMPLE):
                self._sequencer_samples_logic.rename_sample(sample_id, stripped)

    def _request_nes_frequency_change(self, nes_frequency: int) -> None:
        """Applies a NES-frequency change, confirming first when it would re-time existing samples.

        The rate governs how every sample plays back, so changing it on a project that already
        holds samples prompts once (until acknowledged for the session); an empty or acknowledged
        project applies silently. Cancelling restores the field to the project's current value.
        """
        if nes_frequency == self._sequencer_grid_logic.settings.nes_frequency:
            return

        if self._nes_frequency_change_acknowledged or not self._project_controller.has_samples:
            self._perform_nes_frequency_change(nes_frequency)
            return

        self._dialogs.show_confirmation(
            tag=TAG_SEQUENCER_MODULE_DIALOG_NES_FREQUENCY,
            title=self._ttl_change_nes_frequency,
            message=self._msg_change_nes_frequency,
            on_confirm=lambda: self._perform_nes_frequency_change(nes_frequency),
            ok_label=self._lbl_change_nes_frequency,
            opt_out_label=self._lbl_dont_ask_again,
            on_opt_out=self._acknowledge_nes_frequency_changes,
            on_cancel=self._sequencer_grid_logic.push_settings,
        )

    def _perform_nes_frequency_change(self, nes_frequency: int) -> None:
        with self._history.transaction(HistoryAction.SET_NES_FREQUENCY, detail=str(nes_frequency)):
            self._sequencer_grid_logic.set_nes_frequency(nes_frequency)

    def _acknowledge_nes_frequency_changes(self) -> None:
        self._nes_frequency_change_acknowledged = True

    def _on_order_remove(self, position: int) -> None:
        length_before = self._project_controller.order_length
        self._sequencer_order_logic.remove_from_order(position)
        self._relocate_playhead(
            lambda playhead: remap_after_remove(
                playhead,
                position,
                length_before - 1,
            )
        )

    def _on_order_duplicate(self, position: int) -> None:
        self._sequencer_order_logic.duplicate_frame(position)
        self._relocate_playhead(
            lambda playhead: remap_after_insert(
                playhead,
                position + 1,
            )
        )
        self._select_frame_when_idle(position + 1)

    def _on_order_insert(self, position: int) -> None:
        self._sequencer_order_logic.insert_frame(position + 1)
        self._relocate_playhead(
            lambda playhead: remap_after_insert(
                playhead,
                position + 1,
            )
        )
        self._select_frame_when_idle(position + 1)

    def _on_order_clear(self, position: int) -> None:
        """Clears every channel in the frame; no index shift, so the playhead is left in place.

        A sounding voice keeps ringing across the now-empty frame (only an explicit note-off cuts it).
        """
        self._sequencer_order_logic.clear_frame(position)

    def _on_order_move(self, from_position: int, to_position: int) -> None:
        self._sequencer_order_logic.move_frame(from_position, to_position)
        self._relocate_playhead(
            lambda playhead: remap_after_move(
                playhead,
                from_position,
                to_position,
            )
        )
        self._sequencer_grid_logic.select_frame(to_position)

    def _on_order_play_from(self, position: int) -> None:
        """Plays from a frame: relocates the playhead when already playing, else starts there."""
        if self._song_player_logic.is_playing():
            self._song_player_logic.seek(position)
        else:
            self._song_player_logic.play_from(position)

    def _relocate_playhead(self, remap: Callable[[int], int]) -> None:
        """Keeps the live playhead on the frame it was sounding after a structural order edit.

        The new position is reflected in the playing highlight straight away, ahead of the worker's
        next row update, so rapid edits (e.g. a held Alt+arrow) stay in step.
        """
        if self._playing_order is None:
            return

        new_order = remap(self._playing_order)
        if new_order == self._playing_order:
            return

        self._playing_order = new_order
        self._song_player_logic.relocate(new_order)
        self._sequencer_order_panel.set_playing_position(new_order)

    def _select_frame_when_idle(self, frame_index: int) -> None:
        """Moves the editor selection to a frame, unless playback is actively driving it."""
        if not self._song_player_logic.is_playing():
            self._sequencer_grid_logic.select_frame(frame_index)

    def _on_tracker_cell_focused(
        self,
        row_index: int,
        generator: Optional[GeneratorName],
    ) -> None:
        """Drops the order cursor and sample selection when the tracker grid takes focus.

        The tracker, order, and samples panels share global key handlers; mutually
        exclusive selections ensure only the focused panel consumes keystrokes.
        """
        self._sequencer_order_panel.deselect_cell()
        self._sequencer_samples_panel.deselect()

    def _on_order_cell_focused(self) -> None:
        """Drops the tracker cursor and sample selection when the order grid takes focus."""
        self._sequencer_grid_panel.deselect_cell()
        self._sequencer_samples_panel.deselect()

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
                        self._sequencer_history_panel.create_panel()

    @property
    def player_panel(self) -> AudioPlayerPanelProtocol:
        return self._player_panel
