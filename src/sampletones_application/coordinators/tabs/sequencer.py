from pathlib import Path
from typing import Callable, Optional, ParamSpec, Tuple, Union

import dearpygui.dearpygui as dpg

from sampletones_application.categories.elements.sequencer import (
    SequencerHistoryElements,
)
from sampletones_application.categories.hierarchy import Page, Panel, Tab, TextType
from sampletones_application.categories.manager import LanguageManager
from sampletones_application.config.managers.config import ConfigManager
from sampletones_application.config.managers.session import SessionManager
from sampletones_application.constants.playback import FollowMode
from sampletones_application.coordinators.edit.protocol import EditSurfaceProtocol
from sampletones_application.coordinators.original_audio import OriginalAudioLocator
from sampletones_application.coordinators.playback.guard import GuardedPlayer
from sampletones_application.coordinators.playback.protocol import AudioPlayerProtocol
from sampletones_application.logic.history.action import HistoryAction
from sampletones_application.logic.history.manager import HistoryManager
from sampletones_application.logic.history.transaction import CoalesceKey
from sampletones_application.logic.project.controller import ProjectController
from sampletones_application.logic.reconstruction.browser_manager import BrowserManager
from sampletones_application.logic.sequencer.browser import SequencerBrowserLogic
from sampletones_application.logic.sequencer.channels import SequencerChannelsLogic
from sampletones_application.logic.sequencer.clipboard import SequencerClipboard
from sampletones_application.logic.sequencer.history_detail import (
    SequencerHistoryDetail,
)
from sampletones_application.logic.sequencer.order import (
    OrderBlockReader,
    OrderBlockWriter,
    SequencerOrderLogic,
)
from sampletones_application.logic.sequencer.playback.playhead import (
    remap_after_insert,
    remap_after_move,
    remap_after_remove,
)
from sampletones_application.logic.sequencer.playback.song_player import SongPlayerLogic
from sampletones_application.logic.sequencer.playback.synthesizer import RowSynthesizer
from sampletones_application.logic.sequencer.samples import SequencerSamplesLogic
from sampletones_application.logic.sequencer.tracker import (
    SequencerTrackerLogic,
    TrackerBlockReader,
    TrackerBlockWriter,
    TrackerRegionAdjuster,
)
from sampletones_application.logic.shared.tree import TreeLogic
from sampletones_application.parameters.sequencer import SequencerTabParameters
from sampletones_application.services.song_player.player import SongPlayerService
from sampletones_application.tags.compose import compose_tag
from sampletones_application.tags.general import (
    SUF_PANEL_CENTER,
    SUF_PANEL_LEFT,
    SUF_PANEL_RIGHT,
    TAG_GLOBAL_DIALOG_NO_PROJECT_OPEN,
    TAG_GLOBAL_TAB_SEQUENCER,
    TAG_GLOBAL_TABS,
    TAG_GLOBAL_THEME_DEFAULT,
    TAG_GLOBAL_THEME_PANEL_GROUND,
    TAG_GLOBAL_THEME_PANEL_SURFACE,
)
from sampletones_application.tags.sequencer import (
    TAG_SEQUENCER_BROWSER_DIALOG_FREQUENCY,
    TAG_SEQUENCER_BROWSER_PANEL,
    TAG_SEQUENCER_HISTORY_PANEL,
    TAG_SEQUENCER_INSTRUMENTS_DIALOG_REMOVE,
    TAG_SEQUENCER_INSTRUMENTS_PANEL,
    TAG_SEQUENCER_MODULE_DIALOG_NES_FREQUENCY,
    TAG_SEQUENCER_MODULE_PANEL,
    TAG_SEQUENCER_ORDER_WINDOW_ORDER_CARD,
    TAG_SEQUENCER_TRACKER_PANEL,
)
from sampletones_application.ui.elements.layout.columns import ColumnSpec, TabColumns
from sampletones_application.ui.elements.layout.responsive import expanded_side_width
from sampletones_application.ui.elements.status import GUIStatusBar
from sampletones_application.ui.panels.sequencer.browser import GUISequencerBrowserPanel
from sampletones_application.ui.panels.sequencer.history import GUISequencerHistoryPanel
from sampletones_application.ui.panels.sequencer.module import GUISequencerModulePanel
from sampletones_application.ui.panels.sequencer.order import GUISequencerOrderPanel
from sampletones_application.ui.panels.sequencer.samples import GUISequencerSamplesPanel
from sampletones_application.ui.panels.sequencer.tracker import GUISequencerTrackerPanel
from sampletones_application.ui.themes.registry import ThemeRegistry
from sampletones_application.utils.gui.dialogs import DialogsRenderer
from sampletones_application.utils.gui.dpg import dpg_configure_item
from sampletones_application.utils.gui.frame import FrameCallbackManager
from sampletones_application.utils.gui.keyboard import ActivePredicate, KeyRouter
from sampletones_application.utils.gui.shortcuts.source import ShortcutSource
from sampletones_application.view_model.sequencer.channels import (
    SequencerChannelsViewModel,
)
from sampletones_application.view_model.sequencer.history import (
    HistoryEntryViewModel,
    HistoryViewModel,
)
from sampletones_application.view_model.sequencer.region import (
    OrderCell,
    OrderRegion,
    TrackerCell,
    TrackerRegion,
)
from sampletones_application.view_model.sequencer.samples import (
    SequencerSamplesViewModel,
)
from sampletones_application.view_model.sequencer.settings import (
    SequencerSettingsViewModel,
)
from sampletones_application.view_model.sequencer.song_player import SongPlayerViewModel
from sampletones_application.view_model.shared.history import (
    HistoryDetail,
    HistoryDetailSegment,
    HistoryDetailWordSegment,
)
from sampletones_core.audio import AudioDeviceManager
from sampletones_core.constants.enums import FeatureKey, GeneratorName
from sampletones_core.project.song_position import SongPosition
from sampletones_core.reconstructions import Reconstruction
from sampletones_shared.exceptions import SampleToNESError
from sampletones_shared.logger import logger
from sampletones_shared.types.callback import StringCallback, VoidCallback

_UndoableParams = ParamSpec("_UndoableParams")

_LEFT_COLUMN_TAG = compose_tag(TAG_GLOBAL_TAB_SEQUENCER, SUF_PANEL_LEFT)
_CENTER_COLUMN_TAG = compose_tag(TAG_GLOBAL_TAB_SEQUENCER, SUF_PANEL_CENTER)
_RIGHT_COLUMN_TAG = compose_tag(TAG_GLOBAL_TAB_SEQUENCER, SUF_PANEL_RIGHT)


class SequencerTabCoordinator:
    def __init__(
        self,
        config_manager: ConfigManager,
        session_manager: SessionManager,
        audio_device_manager: AudioDeviceManager,
        key_router: KeyRouter,
        shortcut_source: ShortcutSource,
        browser_manager: BrowserManager,
        project_controller: ProjectController,
        history: HistoryManager,
        original_audio_locator: OriginalAudioLocator,
        *,
        tab_active: ActivePredicate,
        layout: SequencerTabParameters,
        language_manager: LanguageManager,
        dialogs: DialogsRenderer,
        status_bar: GUIStatusBar,
        on_edit_sample_requested: StringCallback,
        on_sample_reconstruction_replaced: Callable[[str, Reconstruction], None],
        on_tab_switch: Callable[[Tab], None],
        on_nes_frequency_changed: Callable[[int], None],
        on_channels_changed: VoidCallback,
    ) -> None:
        self._project_controller = project_controller
        self._session_manager = session_manager
        self._history = history
        self._original_audio_locator = original_audio_locator
        self._on_edit_sample_requested = on_edit_sample_requested
        self._on_sample_reconstruction_replaced = on_sample_reconstruction_replaced
        self._on_tab_switch = on_tab_switch
        self._on_nes_frequency_changed = on_nes_frequency_changed
        self._on_channels_changed = on_channels_changed
        self._language_manager = language_manager
        self._dialogs = dialogs

        self._msg_no_project = language_manager["global.dialog.message.no_project_open"]
        self._ttl_no_project = language_manager["global.dialog.title.no_project_open"]
        self._nes_frequency_change_acknowledged: bool = False
        self._playing_position: Optional[SongPosition] = None
        self._geometry = layout.geometry
        self._side_panel_count: int
        self._instruments_width = layout.right_column_width
        self._right_height = layout.right_column_height
        self._history_expanded_height = layout.history_height
        self._history_collapsed_footprint = layout.header_bar_height + 2 * self._geometry.panel_gap
        self._inter_card_gap = self._stacked_card_gap()

        self._sequencer_browser_logic: SequencerBrowserLogic = SequencerBrowserLogic(
            config_manager,
            browser_manager,
            project_controller,
        )
        self._sequencer_tree_logic: TreeLogic = TreeLogic(
            session_manager,
            audio_device_manager,
            scheduling=layout.scheduling,
        )
        self._sequencer_browser_panel: GUISequencerBrowserPanel = GUISequencerBrowserPanel(
            self._sequencer_browser_logic.tree,
            self._sequencer_tree_logic,
            scheduling=layout.scheduling,
            language_manager=language_manager,
            status_bar=status_bar,
            colors=layout.tree_colors,
            initial_collapsed=session_manager.is_card_collapsed(TAG_SEQUENCER_BROWSER_PANEL),
        )
        self._sequencer_tracker_logic: SequencerTrackerLogic = SequencerTrackerLogic(project_controller)
        self._sequencer_order_logic: SequencerOrderLogic = SequencerOrderLogic(project_controller)
        self._clipboard: SequencerClipboard = SequencerClipboard()
        self._tracker_block_reader: TrackerBlockReader = TrackerBlockReader(self._sequencer_tracker_logic)
        self._tracker_block_writer: TrackerBlockWriter = TrackerBlockWriter(self._sequencer_tracker_logic)
        self._tracker_region_adjuster: TrackerRegionAdjuster = TrackerRegionAdjuster(self._sequencer_tracker_logic)
        self._order_block_reader: OrderBlockReader = OrderBlockReader(self._sequencer_order_logic)
        self._order_block_writer: OrderBlockWriter = OrderBlockWriter(self._sequencer_order_logic)
        self._sequencer_samples_logic: SequencerSamplesLogic = SequencerSamplesLogic(
            project_controller,
            session_manager,
            audio_device_manager,
            scheduling=layout.scheduling,
        )
        self._sequencer_channels_logic: SequencerChannelsLogic = SequencerChannelsLogic()
        self._song_player_logic: SongPlayerLogic = SongPlayerLogic(
            audio_device_manager,
            project_controller,
            session_manager,
            service=SongPlayerService(
                audio_device_manager,
                RowSynthesizer(
                    project_controller,
                    config_manager.config,
                    active_channels=lambda: self._sequencer_channels_logic.active_channels,
                    sample_rate=lambda: audio_device_manager.sample_rate,
                ),
                should_loop=lambda: session_manager.loop_song,
                master_gain=lambda: session_manager.master_gain,
            ),
        )
        self._guarded_player = GuardedPlayer(
            self._song_player_logic,
            dialogs=dialogs,
            error_message=language_manager["global.player.message.audio_playback_error"],
        )
        self._sequencer_tracker_panel: GUISequencerTrackerPanel = GUISequencerTrackerPanel(
            self._sequencer_tracker_logic.settings,
            layout=layout.sequencer,
            initial_collapsed=session_manager.is_card_collapsed(TAG_SEQUENCER_TRACKER_PANEL),
            language_manager=language_manager,
            key_router=key_router,
            tab_active=tab_active,
            shortcut_source=shortcut_source,
        )
        self._sequencer_module_panel: GUISequencerModulePanel = GUISequencerModulePanel(
            self._sequencer_tracker_logic.settings,
            layout=layout.sequencer,
            inputs=layout.inputs,
            initial_collapsed=session_manager.is_card_collapsed(TAG_SEQUENCER_MODULE_PANEL),
            language_manager=language_manager,
            status_bar=status_bar,
        )
        self._sequencer_order_panel: GUISequencerOrderPanel = GUISequencerOrderPanel(
            layout=layout.sequencer,
            plus_minus_layout=layout.plus_minus,
            initial_collapsed=session_manager.is_card_collapsed(TAG_SEQUENCER_ORDER_WINDOW_ORDER_CARD),
            language_manager=language_manager,
            key_router=key_router,
            tab_active=tab_active,
            shortcut_source=shortcut_source,
        )
        self._sequencer_samples_panel: GUISequencerSamplesPanel = GUISequencerSamplesPanel(
            layout=layout.sequencer,
            initial_collapsed=session_manager.is_card_collapsed(TAG_SEQUENCER_INSTRUMENTS_PANEL),
            language_manager=language_manager,
            key_router=key_router,
            tab_active=tab_active,
            shortcut_source=shortcut_source,
        )
        self._sequencer_history_panel: GUISequencerHistoryPanel = GUISequencerHistoryPanel(
            layout=layout.sequencer,
            feature_colors=layout.feature_colors,
            initial_collapsed=session_manager.is_card_collapsed(TAG_SEQUENCER_HISTORY_PANEL),
            language_manager=language_manager,
            status_bar=status_bar,
        )
        self._history_detail: SequencerHistoryDetail = SequencerHistoryDetail(
            self._sequencer_tracker_logic,
            self._sequencer_samples_logic,
        )

        self._wire_callbacks()

    def _wire_callbacks(self) -> None:
        """Connects every panel and logic object this tab owns to the handler that serves it."""
        self._wire_collapse_handlers()
        self._wire_module_callbacks()
        self._wire_tracker_callbacks()
        self._wire_channels_callbacks()
        self._wire_order_callbacks()
        self._wire_block_callbacks()
        self._wire_samples_callbacks()
        self._wire_browser_callbacks()
        self._wire_playback_callbacks()
        self._wire_project_callbacks()
        self._wire_history()

    def _wire_collapse_handlers(self) -> None:
        for panel in (
            self._sequencer_order_panel,
            self._sequencer_tracker_panel,
            self._sequencer_module_panel,
            self._sequencer_samples_panel,
            self._sequencer_history_panel,
        ):
            panel.set_collapse_handler(self._on_card_collapse_changed)

    def _wire_module_callbacks(self) -> None:
        self._sequencer_module_panel.on_nes_frequency = self._request_nes_frequency_change
        self._sequencer_module_panel.on_rows_per_pattern = self._undoable(
            HistoryAction.SET_ROWS_PER_PATTERN,
            self._sequencer_tracker_logic.set_rows_per_pattern,
            detail=self._history_detail.value,
            coalesce=self._module_setting_key,
        )
        self._sequencer_module_panel.on_tempo = self._undoable(
            HistoryAction.SET_TEMPO,
            self._sequencer_tracker_logic.set_tempo,
            detail=self._history_detail.value,
            coalesce=self._module_setting_key,
        )
        self._sequencer_module_panel.on_speed = self._undoable(
            HistoryAction.SET_SPEED,
            self._sequencer_tracker_logic.set_speed,
            detail=self._history_detail.value,
            coalesce=self._module_setting_key,
        )

    def _wire_tracker_callbacks(self) -> None:
        self._sequencer_tracker_panel.on_clear_row = self._undoable(
            HistoryAction.CLEAR_ROW,
            self._sequencer_tracker_logic.clear_cell,
            detail=self._history_detail.clear_row,
        )
        self._sequencer_tracker_panel.on_clear_subcolumn = self._undoable(
            HistoryAction.CLEAR_SUBCOLUMN,
            self._sequencer_tracker_logic.clear_cell_subcolumn,
            detail=self._history_detail.clear_subcolumn,
        )
        self._sequencer_tracker_panel.on_set_row = self._undoable(
            HistoryAction.EDIT_ROW,
            self._sequencer_tracker_logic.write_cell,
            detail=self._history_detail.edit_row,
            coalesce=self._edit_row_key,
        )
        self._sequencer_tracker_panel.on_set_note_off = self._undoable(
            HistoryAction.NOTE_OFF,
            self._sequencer_tracker_logic.cut_note,
            detail=self._history_detail.note_off,
            coalesce=self._cell_key,
        )
        self._sequencer_tracker_panel.on_cell_selected = self._on_tracker_cell_focused
        self._sequencer_tracker_panel.on_play_from_row = self._on_tracker_play_from_row
        self._sequencer_tracker_panel.on_play_from_frame = self.play_from_current_frame
        self._sequencer_tracker_panel.on_adjust_transpose = self._undoable(
            HistoryAction.ADJUST_TRANSPOSE,
            self._tracker_region_adjuster.adjust_transpose,
            detail=self._history_detail.adjust_transpose,
            coalesce=self._adjustment_key,
        )
        self._sequencer_tracker_panel.on_adjust_volume = self._undoable(
            HistoryAction.ADJUST_VOLUME,
            self._tracker_region_adjuster.adjust_volume,
            detail=self._history_detail.adjust_volume,
            coalesce=self._adjustment_key,
        )
        self._sequencer_tracker_logic.on_settings_changed = self._on_settings_changed
        self._sequencer_tracker_logic.on_tracker_changed = self._sequencer_tracker_panel.update_tracker
        self._sequencer_tracker_logic.on_frame_changed = self._sequencer_order_panel.select_position

    def _wire_channels_callbacks(self) -> None:
        """Connects the tracker's column headers and the order table's row labels to the mute set
        the song player reads.

        Both tables name the same channels and switch the same set, so each panel's hooks reach the
        channels logic directly and both show every change. Muting is a monitoring gesture, so these
        hooks record no history entry.
        """
        self._sequencer_channels_logic.on_channels_changed = self._show_channels
        for panel in (self._sequencer_tracker_panel, self._sequencer_order_panel):
            panel.on_channel_mute_toggled = self._sequencer_channels_logic.toggle
            panel.on_channel_soloed = self._sequencer_channels_logic.solo
            panel.on_channels_toggled = self._sequencer_channels_logic.toggle_all
            panel.on_channels_muted = self._sequencer_channels_logic.mute_all
            panel.on_channels_unmuted = self._sequencer_channels_logic.unmute_all

    def _show_channels(self, view_model: SequencerChannelsViewModel) -> None:
        """Shows the mute set in both tables and in the menu bar, so a channel reads the same
        wherever it appears.

        The menu bar sits above this tab and rebuilds its own state, so it is handed the change
        as a signal and reads the mute set back through :attr:`channels`.
        """
        self._sequencer_tracker_panel.update_channels(view_model)
        self._sequencer_order_panel.update_channels(view_model)
        self._on_channels_changed()

    @property
    def channels(self) -> SequencerChannelsViewModel:
        """The mute set the tables show, for the menu bar that lists the same channels."""
        return self._sequencer_channels_logic.build_channels()

    def toggle_channel(self, generator: GeneratorName) -> None:
        """Flips one channel between audible and silent, the menu's per-channel gesture."""
        self._sequencer_channels_logic.toggle(generator)

    def unmute_all_channels(self) -> None:
        """Returns every channel to audible, the menu's whole-mix gesture."""
        self._sequencer_channels_logic.unmute_all()

    def set_follow_mode(self, mode: FollowMode) -> None:
        """Chooses how far the view chases the playhead, the menu's and keyboard's gesture.

        The player holds the setting and emits a view as it changes, which is what settles the
        grid's following and the menu's mark together.
        """
        self._song_player_logic.set_follow_mode(mode)

    def _wire_order_callbacks(self) -> None:
        self._sequencer_order_logic.on_order_changed = self._sequencer_order_panel.update_order
        self._sequencer_order_panel.on_frame_selected = self._on_order_frame_selected
        self._sequencer_order_panel.on_remove_requested = self._undoable(
            HistoryAction.REMOVE_FRAME,
            self._on_order_remove,
            detail=self._history_detail.remove_frame,
        )
        self._sequencer_order_panel.on_duplicate_requested = self._undoable(
            HistoryAction.DUPLICATE_FRAME,
            self._on_order_duplicate,
            detail=self._history_detail.copy_frame,
        )
        self._sequencer_order_panel.on_clone_requested = self._undoable(
            HistoryAction.CLONE_FRAME,
            self._on_order_clone,
            detail=self._history_detail.copy_frame,
        )
        self._sequencer_order_panel.on_insert_requested = self._undoable(
            HistoryAction.ADD_FRAME,
            self._on_order_insert,
            detail=self._history_detail.add_frame,
        )
        self._sequencer_order_panel.on_clear_requested = self._undoable(
            HistoryAction.CLEAR_FRAME,
            self._on_order_clear,
            detail=self._history_detail.clear_frame,
        )
        self._sequencer_order_panel.on_play_from_requested = self._on_order_play_from
        self._sequencer_order_panel.on_move_requested = self._undoable(
            HistoryAction.MOVE_FRAME,
            self._on_order_move,
            detail=self._history_detail.move_frame,
        )
        self._sequencer_order_panel.on_set_order_entry = self._undoable(
            HistoryAction.SET_ORDER_ENTRY,
            self._sequencer_order_logic.set_order_entry,
            detail=self._history_detail.set_order_entry,
        )
        self._sequencer_order_panel.on_set_master_entry = self._undoable(
            HistoryAction.SET_ORDER_ENTRY,
            self._sequencer_order_logic.set_master_entry,
            detail=self._history_detail.set_master_entry,
        )
        self._sequencer_order_panel.on_cell_selected = self._on_order_cell_focused

    def _wire_block_callbacks(self) -> None:
        """Connects the grids' block gestures to the clipboard they copy into.

        A copy reads the project and leaves it as it stands, so it is wired straight through
        instead of through :meth:`_undoable`: a transaction over it would record an entry the
        history has nothing to restore for. The three gestures that do write are whole ones, each
        recording the single entry that takes the grid back to where it stood.

        Each grid also asks whether its own slot holds a block, which is what a menu offering
        Paste consults before it is opened.
        """
        self._sequencer_tracker_panel.can_paste_block = self._can_paste_tracker_block
        self._sequencer_order_panel.can_paste_block = self._can_paste_order_block
        self._sequencer_tracker_panel.on_copy_block = self._on_tracker_copy_block
        self._sequencer_tracker_panel.on_cut_block = self._undoable(
            HistoryAction.CUT_BLOCK,
            self._cut_tracker_block,
            detail=self._history_detail.tracker_block,
        )
        self._sequencer_tracker_panel.on_delete_block = self._undoable(
            HistoryAction.DELETE_BLOCK,
            self._tracker_block_writer.clear,
            detail=self._history_detail.tracker_block,
        )
        self._sequencer_tracker_panel.on_paste_block = self._undoable(
            HistoryAction.PASTE_BLOCK,
            self._paste_tracker_block,
            detail=self._history_detail.tracker_paste,
        )
        self._sequencer_order_panel.on_copy_block = self._on_order_copy_block
        self._sequencer_order_panel.on_cut_block = self._undoable(
            HistoryAction.CUT_BLOCK,
            self._cut_order_block,
            detail=self._history_detail.order_block,
        )
        self._sequencer_order_panel.on_delete_block = self._undoable(
            HistoryAction.DELETE_BLOCK,
            self._order_block_writer.clear,
            detail=self._history_detail.order_block,
        )
        self._sequencer_order_panel.on_paste_block = self._undoable(
            HistoryAction.PASTE_BLOCK,
            self._paste_order_block,
            detail=self._history_detail.order_paste,
        )

    def _can_paste_tracker_block(self) -> bool:
        """Whether the tracker has a block to write, which is what its Paste item is offered on."""
        return self._clipboard.tracker_block is not None

    def _can_paste_order_block(self) -> bool:
        """Whether the order has a block to write, which is what its Paste item is offered on."""
        return self._clipboard.order_block is not None

    def _on_tracker_copy_block(self, region: TrackerRegion) -> None:
        """Puts the tracker's selected block on the clipboard, for a paste to replay."""
        self._clipboard.store_tracker_block(self._tracker_block_reader.read(region))

    def _cut_tracker_block(self, region: TrackerRegion) -> None:
        """Takes the block a region covers onto the clipboard, then empties what it covered."""
        self._on_tracker_copy_block(region)
        self._tracker_block_writer.clear(region)

    def _paste_tracker_block(self, cell: TrackerCell) -> None:
        """Writes the block the tracker last copied at a cell, while a copy has been made."""
        block = self._clipboard.tracker_block
        if block is not None:
            self._tracker_block_writer.write(block, cell)

    def _on_order_copy_block(self, region: OrderRegion) -> None:
        """Puts the order's selected block on the clipboard, for a paste to replay."""
        self._clipboard.store_order_block(self._order_block_reader.read(region))

    def _cut_order_block(self, region: OrderRegion) -> None:
        """Takes the block a region covers onto the clipboard, then silences what it covered."""
        self._on_order_copy_block(region)
        self._order_block_writer.clear(region)

    def _paste_order_block(self, cell: OrderCell) -> None:
        """Writes the block the order last copied at a cell, while a copy has been made."""
        block = self._clipboard.order_block
        if block is not None:
            self._order_block_writer.write(block, cell)

    def _wire_samples_callbacks(self) -> None:
        self._sequencer_samples_logic.on_samples_changed = self._on_samples_changed
        self._sequencer_samples_logic.on_edit_sample_requested = self._dispatch_edit_sample
        self._sequencer_samples_logic.on_autoplay_error = self._on_preview_error
        self._sequencer_samples_panel.on_sample_selected = self._on_sample_selected
        self._sequencer_samples_panel.on_sample_edit_requested = self._sequencer_samples_logic.request_edit
        self._sequencer_samples_panel.on_loop_changed = self._undoable(
            HistoryAction.SET_SAMPLE_LOOP,
            self._sequencer_samples_logic.set_sample_loop,
            detail=self._history_detail.set_sample_loop,
        )
        self._sequencer_samples_panel.on_remove_requested = self._remove_sample
        self._sequencer_samples_panel.on_play_requested = self._sequencer_samples_logic.play_sample
        self._sequencer_samples_panel.on_move_requested = self._undoable(
            HistoryAction.MOVE_SAMPLE,
            self._sequencer_samples_logic.move_sample,
            detail=self._history_detail.move_sample,
        )
        self._sequencer_samples_panel.on_rename_committed = self._submit_rename
        self._sequencer_samples_panel.on_duplicate_requested = self._undoable(
            HistoryAction.DUPLICATE_SAMPLE,
            self._sequencer_samples_logic.duplicate_sample,
            detail=self._history_detail.duplicate_sample,
        )

    def _wire_browser_callbacks(self) -> None:
        self._sequencer_browser_panel.set_collapse_handler(self._on_browser_collapse_changed)
        self._sequencer_browser_panel.on_add_to_sequencer = self.import_reconstruction
        self._sequencer_browser_panel.can_add_to_sequencer = self._is_project_open
        self._sequencer_browser_panel.on_replace_in_sequencer = self.replace_reconstruction
        self._sequencer_browser_panel.replace_in_sequencer_label = self._replace_target_label
        self._sequencer_browser_panel.on_locate_original_audio = self._original_audio_locator.locate
        self._sequencer_browser_panel.on_refresh_tree = self._sequencer_browser_logic.refresh_tree
        self._sequencer_tree_logic.on_lock_state_changed = self._sequencer_browser_panel.set_tree_enabled
        self._sequencer_tree_logic.on_favorite_changed = self._sequencer_browser_panel.update_favorite_indicator
        self._sequencer_tree_logic.on_search_update_needed = self._sequencer_browser_panel.update_tree_visibility
        self._sequencer_tree_logic.on_autoplay_error = self._on_preview_error

    def _wire_playback_callbacks(self) -> None:
        self._song_player_logic.on_position_changed = self._on_player_position_changed
        self._song_player_logic.on_view_changed = self._on_player_view_changed
        self._song_player_logic.on_error = self._on_player_error

    def _wire_project_callbacks(self) -> None:
        self._project_controller.on_settings_changed = self._sequencer_tracker_logic.push_settings
        self._project_controller.on_song_changed = self._on_song_changed
        self._project_controller.on_samples_changed = self._sequencer_samples_logic.push_samples
        self._project_controller.on_project_replaced = self._on_project_replaced

    def _on_card_collapse_changed(self, card_tag: str, collapsed: bool) -> None:
        """Persists a card's collapsed state so it restores on the next launch."""
        self._session_manager.set_card_collapsed(card_tag, collapsed)
        if card_tag == TAG_SEQUENCER_HISTORY_PANEL:
            self._sync_samples_height()

    def _on_browser_collapse_changed(self, card_tag: str, collapsed: bool) -> None:
        """Persists the browser panel's collapse, then docks or restores the width of the column it fills."""
        self._session_manager.set_card_collapsed(card_tag, collapsed)
        self._sync_browser_width()

    def sync_responsive_layout(self) -> None:
        """Refits this tab's side column to the current viewport, the entry the resize handler calls."""
        self._sync_browser_width()

    def _sync_browser_width(self) -> None:
        """Shrinks the browser column to the collapse rail when collapsed, else sizes it to the viewport width."""
        if self._sequencer_browser_panel.collapsed:
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

    def _stacked_card_gap(self) -> int:
        """The rendered vertical gap between two cards stacked in the right column.

        The cards are separated by a ``panel_gap`` spacer, but DearPyGui also lays its ``ItemSpacing.y``
        on each side of that spacer, so the real gap is the spacer plus two of those spacings. The
        spacing is read from the base theme, which sets it explicitly, so the gap tracks the theme's
        value.
        """
        spacing = ThemeRegistry.get(TAG_GLOBAL_THEME_DEFAULT).get_style(
            dpg.mvAll,
            dpg.mvStyleVar_ItemSpacing,
        )
        spacing_y = int(spacing[1]) if spacing is not None else 0
        return self._geometry.panel_gap + 2 * spacing_y

    def _sync_samples_height(self) -> None:
        """Reserves the bottom space the history card and its inter-card gap occupy, so samples fills the rest.

        The samples card fills the right column above the history card by reserving that footprint below
        it. History carries its own height in both states — filling the reservation while expanded, pinned
        to its header bar while collapsed — so this only has to size the reservation: the expanded history
        height, or the collapsed bar footprint. The reservation clears the full inter-card gap (see
        :meth:`_stacked_card_gap`) so the collapsed bar lands flush at the column bottom.
        """
        if self._sequencer_history_panel.collapsed:
            footprint = self._history_collapsed_footprint
        else:
            footprint = self._history_expanded_height

        self._sequencer_samples_panel.set_expanded_height(-(self._inter_card_gap + footprint))

    def _wire_history(self) -> None:
        self._sequencer_history_panel.on_undo = self.undo
        self._sequencer_history_panel.on_redo = self.redo
        self._sequencer_history_panel.on_jump_to = self.jump_to_history

    def _undoable(
        self,
        action: HistoryAction,
        callback: Callable[_UndoableParams, None],
        *,
        detail: Optional[Callable[_UndoableParams, HistoryDetail]] = None,
        coalesce: Optional[Callable[_UndoableParams, CoalesceKey]] = None,
    ) -> Callable[_UndoableParams, None]:
        """Wraps a state-changing hook so its whole gesture becomes one undo entry.

        Every mutation the wrapped callback triggers is grouped under ``action``;
        a gesture that changes nothing records no entry. ``detail`` computes the
        entry's coloured description segments from the same arguments the hook
        receives, and ``coalesce`` computes the gesture's target key from them:
        consecutive gestures sharing the same action and target collapse into a
        single entry.

        The gesture is batched inside its transaction, so however many rows it
        writes, the panels rebuild once — and they rebuild before the entry that
        undoes them is recorded, because the snapshot reads the project rather
        than the views.
        """

        def wrapped(
            *args: _UndoableParams.args,
            **kwargs: _UndoableParams.kwargs,
        ) -> None:
            description = detail(*args, **kwargs) if detail is not None else ()
            key = coalesce(*args, **kwargs) if coalesce is not None else None
            with (
                self._history.transaction(
                    action,
                    detail=description,
                    coalesce=key,
                ),
                self._project_controller.batch(),
            ):
                callback(*args, **kwargs)

        return wrapped

    def _cell_key(
        self,
        row_index: int,
        generator: Optional[GeneratorName],
    ) -> CoalesceKey:
        """Identifies one cell of the displayed frame as a coalescing target.

        The sample column (``generator`` absent) is its own target, distinct from
        every channel column.
        """
        channel = generator if generator is not None else ""
        return (self._sequencer_tracker_logic.frame_index, channel, row_index)

    def _adjustment_key(
        self,
        region: TrackerRegion,
        _delta: int,
    ) -> CoalesceKey:
        """Identifies the cells an adjustment covers as one coalescing target.

        A streak of nudges over the same block reads as one entry, so holding a transpose key steps
        the selection and leaves a single step to undo; moving the cursor or reaching the selection
        out starts the next one.
        """
        return (
            self._sequencer_tracker_logic.frame_index,
            region.first_row,
            region.last_row,
            region.first_slot,
            region.last_slot,
        )

    def _edit_row_key(
        self,
        row_index: int,
        generator: Optional[GeneratorName],
        sample_id: Optional[str],
        transpose: Optional[int],
        volume: Optional[int],
    ) -> CoalesceKey:
        """Extends the cell target with the subcolumns the edit writes.

        Consecutive edits of one cell coalesce only when they write the same
        subcolumns, so entering a note and then tweaking its volume stay
        separate entries.
        """
        return (
            *self._cell_key(row_index, generator),
            sample_id is not None,
            transpose is not None,
            volume is not None,
        )

    def _module_setting_key(self, _value: int) -> CoalesceKey:
        """Marks a module-wide setting as one target, shared by its whole streak."""
        return ()

    def _on_settings_changed(
        self,
        view_model: SequencerSettingsViewModel,
    ) -> None:
        """Hands the project's song settings to the two panels that read them.

        The module panel shows the timing fields themselves; the tracker reads the metre out of
        the same view model, so a highlight edited in the project properties retints the grid as
        soon as the dialog commits.
        """
        self._sequencer_module_panel.update_settings(view_model)
        self._sequencer_tracker_panel.update_settings(view_model)

    def _on_project_replaced(self) -> None:
        """Realigns the tab with a replaced project, keeping the mute set across history navigation.

        Undo, redo, and history jumps replace the project as well, and the history manager reports
        itself restoring throughout, so the channels the user is listening through carry across
        them. A new, opened, or closed document begins a fresh listening session instead, with
        every channel audible.
        """
        if not self._history.is_restoring:
            self._sequencer_channels_logic.reset()

        self._history.reset()
        self.refresh()

    def play_from_current_frame(self) -> None:
        """Plays from the frame the tracker is showing, seeking in place when already playing."""
        self._on_order_play_from(self._sequencer_tracker_logic.frame_index)

    def undo(self) -> None:
        self._history.undo()

    def redo(self) -> None:
        self._history.redo()

    def jump_to_history(self, index: int) -> None:
        self._history.jump_to(index)

    def refresh_history(self) -> None:
        """Re-renders the history panel from the manager's current stack.

        Called by the application's history fan-out, which owns the manager's
        single ``on_history_changed`` slot and forwards each change here and to
        the menu bar.
        """
        self._sequencer_history_panel.update_view(self._build_history_view_model())

    def reconstruction_edit_detail(
        self,
        sample_id: str,
        generator_name: GeneratorName,
        feature_key: FeatureKey,
    ) -> HistoryDetail:
        """Describes a reconstruction edit for the project history's detail line."""
        return self._history_detail.edit_reconstruction(
            sample_id,
            generator_name,
            feature_key,
        )

    def _build_history_view_model(self) -> HistoryViewModel:
        cursor = self._history.cursor
        entries = tuple(
            HistoryEntryViewModel(
                index=index,
                label=self._history_action_label(entry.action),
                detail_segments=tuple(self._resolve_detail_segment(segment) for segment in entry.detail),
                is_current=index == cursor,
                is_future=index > cursor,
            )
            for index, entry in enumerate(self._history.entries)
        )
        return HistoryViewModel(entries=entries, cursor=cursor)

    def _history_action_label(self, action: HistoryAction) -> str:
        return self._language_manager[
            Page.SEQUENCER,
            Panel.HISTORY,
            TextType.LABEL,
            action,
        ]

    def _resolve_detail_segment(
        self,
        segment: Union[HistoryDetailSegment, HistoryDetailWordSegment],
    ) -> HistoryDetailSegment:
        if isinstance(segment, HistoryDetailWordSegment):
            text = self._language_manager[
                Page.SEQUENCER,
                Panel.HISTORY,
                TextType.LABEL,
                SequencerHistoryElements(segment.word.value),
            ]
            return HistoryDetailSegment(text=text, role=segment.role)

        return segment

    def initialize(self) -> None:
        """Pushes the current project into every sequencer panel.

        Called once after the GUI is built so the panels reflect the project the
        application started with (or restored).
        """
        self._song_player_logic.refresh_view()
        self.refresh()

    def refresh(self) -> None:
        self._nes_frequency_change_acknowledged = False
        self._song_player_logic.stop()
        self._sequencer_tracker_logic.refresh()
        self._sequencer_order_logic.refresh()
        self._sequencer_samples_logic.push_samples()
        self._sequencer_channels_logic.push_channels()
        is_open = self._project_controller.is_open
        self._sequencer_module_panel.set_enabled(is_open)
        self._sequencer_tracker_panel.set_enabled(is_open)
        self._sequencer_order_panel.set_enabled(is_open)
        self._sequencer_history_panel.set_enabled(is_open)

    def repaint(self) -> None:
        """Draws every table again so its tints take the palette now in place.

        DearPyGui keeps a table's row, column and cell tints as state of the table rather than
        as a property of an item, so they take a new colour by being issued again. Each panel
        answers for the tints it owns, and this is where the palette asks all three.
        """
        self._sequencer_tracker_panel.repaint()
        self._sequencer_order_panel.repaint()
        self._sequencer_samples_panel.repaint()

    def refresh_browser(self) -> None:
        self._sequencer_browser_panel.refresh()

    def _on_song_changed(self) -> None:
        self._sequencer_tracker_logic.push_settings()
        self._sequencer_tracker_logic.push_tracker()
        self._sequencer_order_logic.push_order()

    def _on_player_error(self, error: Exception) -> None:
        self._dialogs.show_error(error)

    def _on_player_view_changed(self, view_model: SongPlayerViewModel) -> None:
        """Settles the marks the transport owns, and how far the grid chases the playhead.

        The player emits a view on every position update and on every change to the setting, so
        reading the follow behaviour here keeps the grid in step both while a song sounds and the
        moment the reader picks another mode.
        """
        self._sequencer_tracker_panel.set_row_following(view_model.follow_mode.follows_row)
        if not view_model.is_playing and not view_model.is_paused:
            self._playing_position = None
            self._mark_playhead()

    def _on_player_position_changed(
        self,
        order_position: int,
        row_index: int,
    ) -> None:
        """Moves the marks the playhead carries, showing the frame it sounds when following.

        The frame is selected ahead of the marks so the row's mark, and the scroll that reveals it,
        land on the pattern the playhead has reached.
        """
        self._playing_position = SongPosition(
            order_position=order_position,
            row_index=row_index,
        )
        if self._song_player_logic.follow_mode.follows_pattern:
            self._sequencer_tracker_logic.select_frame(order_position)

        self._mark_playhead()

    def _mark_playhead(self) -> None:
        """Puts the playhead's marks where it stands, on both grids.

        The order grid marks the frame the playhead sounds; the tracker takes the whole position,
        since the row it marks belongs to the pattern of that frame.
        """
        position = self._playing_position
        self._sequencer_tracker_panel.set_playing_position(position)
        self._sequencer_order_panel.set_playing_position(
            position.order_position if position is not None else None,
        )

    def _on_order_frame_selected(self, frame_index: int) -> None:
        """Selects an order frame in the tracker, and moves the playhead too when following.

        While the view follows the playhead, choosing another order during playback relocates the
        playhead to it (the seek no-ops when stopped); otherwise the selection only changes which
        pattern is edited, leaving playback where it is.
        """
        self._sequencer_tracker_logic.select_frame(frame_index)
        if self._song_player_logic.follow_mode.follows_pattern:
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
        except (SampleToNESError, OSError) as exception:
            logger.error_with_traceback(
                exception,
                f"Failed to load reconstruction from {filepath}",
            )
            self._dialogs.show_error(exception)
            return

        self._add_reconstruction_with_frequency_check(reconstruction, filepath.stem)

    def import_reconstruction_object(self, reconstruction: Reconstruction, name: str) -> None:
        """Adds an in-memory reconstruction — the one open in the Reconstruction tab — as a sample.

        The sample embeds an independent copy, so the open document keeps its own source-audio
        location and file backing while the project stores a self-contained, detached sample.
        """
        if not self._project_controller.is_open:
            self._dialogs.show_info(
                TAG_GLOBAL_DIALOG_NO_PROJECT_OPEN,
                self._msg_no_project,
                self._ttl_no_project,
            )
            return

        self._add_reconstruction_with_frequency_check(
            reconstruction.model_copy(deep=True),
            name,
        )

    def _add_reconstruction_with_frequency_check(
        self,
        reconstruction: Reconstruction,
        name: str,
    ) -> None:
        """Adds a loaded reconstruction once its NES frequency is settled against the project's.

        An empty project adopts the incoming frequency, since the rate times nothing there yet; a
        project that already holds samples confirms first, because the rate governs how all of them
        play back.
        """
        self._reconcile_nes_frequency(
            reconstruction,
            lambda adopt_frequency: self._commit_add_reconstruction(
                reconstruction,
                name,
                adopt_frequency=adopt_frequency,
            ),
            can_adopt_frequency=not self._project_controller.has_samples,
        )

    def _reconcile_nes_frequency(
        self,
        reconstruction: Reconstruction,
        commit: Callable[[Optional[int]], None],
        *,
        can_adopt_frequency: bool,
    ) -> None:
        """Settles a reconstruction's NES frequency against the project's, then commits the gesture.

        A reconstruction renders at the frequency it was generated at, so bringing one recorded at
        another rate into the project plays it back wrong. Equal rates commit straight away. A
        mismatch the project can absorb — because the rate times nothing that outlives the gesture —
        adopts the incoming rate. Otherwise the user decides, seeing both rates, and confirming
        keeps the project's rate for the samples already timed by it.

        Args:
            reconstruction: The reconstruction being brought into the project.
            commit: Performs the gesture, receiving the frequency to adopt, or ``None`` to keep the
                project's.
            can_adopt_frequency: Whether adopting the incoming rate re-times only what this gesture
                itself brings in, which settles a mismatch without asking.
        """
        reconstruction_frequency = reconstruction.config.nes_frequency
        project_frequency = self._sequencer_tracker_logic.settings.nes_frequency

        if reconstruction_frequency == project_frequency:
            commit(None)
            return

        if can_adopt_frequency:
            commit(reconstruction_frequency)
            return

        self._dialogs.show_confirmation(
            tag=TAG_SEQUENCER_BROWSER_DIALOG_FREQUENCY,
            title=self._language_manager["global.dialog.title.frequency_mismatch"],
            message=self._language_manager["global.dialog.message.frequency_mismatch"].format(
                reconstruction=reconstruction_frequency,
                project=project_frequency,
            ),
            on_confirm=lambda: commit(None),
            ok_label=self._language_manager["global.dialog.label.add_anyway"],
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
        with self._history.transaction(
            HistoryAction.ADD_SAMPLE,
            detail=self._history_detail.add_sample(name),
        ):
            if adopt_frequency is not None:
                self._sequencer_tracker_logic.set_nes_frequency(adopt_frequency)
            self._sequencer_browser_logic.add_reconstruction(reconstruction, name)

        self._on_tab_switch(Tab.SEQUENCER)

    def replace_reconstruction(self, filepath: Path) -> None:
        """Substitutes the selected sample's reconstruction with a browser file's.

        The sample keeps its id and position, so every pattern row referencing it sounds the
        incoming audio while the tracker shows it where it was, and it takes the file's name the way
        an import does. The target is whatever the samples panel has selected as the gesture starts,
        which is also what named the menu item the user clicked.
        """
        selection = self._sequencer_samples_panel.selection
        if selection is None:
            return

        try:
            reconstruction = self._sequencer_browser_logic.load_reconstruction(filepath)
        except (SampleToNESError, OSError) as exception:
            logger.error_with_traceback(exception, f"Failed to load reconstruction from {filepath}")
            self._dialogs.show_error(exception)
            return

        self._reconcile_nes_frequency(
            reconstruction,
            lambda adopt_frequency: self._commit_replace_reconstruction(
                selection.sample_id,
                reconstruction,
                filepath.stem,
                adopt_frequency=adopt_frequency,
            ),
            can_adopt_frequency=self._project_controller.sample_count == 1,
        )

    def _commit_replace_reconstruction(
        self,
        sample_id: str,
        reconstruction: Reconstruction,
        name: str,
        *,
        adopt_frequency: Optional[int],
    ) -> None:
        """Substitutes a sample's reconstruction as one undoable gesture, renaming it to the source.

        The detail is composed while the sample still holds the outgoing reconstruction, so it reads
        the name being replaced alongside the incoming one. The replacement is announced in the same
        window, ahead of the substitution, because an editor holding the sample open recognises it by
        the identity of the reconstruction it is about to give up. The frequency adoption, the rename,
        and the substitution share a single history entry, so one undo restores the previous rate,
        name, and audio together.
        """
        detail = self._history_detail.replace_sample(sample_id, name)
        with self._history.transaction(
            HistoryAction.REPLACE_SAMPLE,
            detail=detail,
        ):
            if adopt_frequency is not None:
                self._sequencer_tracker_logic.set_nes_frequency(adopt_frequency)

            self._sequencer_samples_logic.rename_sample(sample_id, name)
            self._on_sample_reconstruction_replaced(sample_id, reconstruction)
            self._sequencer_browser_logic.replace_reconstruction(sample_id, reconstruction)

    def _replace_target_label(self) -> Optional[str]:
        """The indexed label of the sample a browser replacement would overwrite, while one is selected."""
        selection = self._sequencer_samples_panel.selection
        if selection is None:
            return None

        return selection.label

    def _dispatch_edit_sample(self, sample_id: str) -> None:
        self._on_edit_sample_requested(sample_id)

    def _on_tracker_play_from_row(self, row_index: int) -> None:
        """Starts playback from the right-clicked row of the frame the tracker is showing."""
        self._song_player_logic.play_from(
            self._sequencer_tracker_logic.frame_index,
            row_index,
        )

    def _on_samples_changed(
        self,
        view_model: SequencerSamplesViewModel,
    ) -> None:
        self._sequencer_samples_panel.update_view(view_model)
        self._sequencer_tracker_panel.update_samples(view_model)

    def _on_sample_selected(self, sample_id: str) -> None:
        self._sequencer_tracker_panel.deselect_cell()
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
            title=self._language_manager["global.dialog.title.remove_sample"],
            message=self._language_manager["global.dialog.message.remove_sample"].format(name=name),
            on_confirm=lambda: self._perform_remove_sample(sample_id),
            ok_label=self._language_manager["global.dialog.label.remove"],
        )

    def _perform_remove_sample(self, sample_id: str) -> None:
        detail = self._history_detail.remove_sample(sample_id)
        with self._history.transaction(
            HistoryAction.REMOVE_SAMPLE,
            detail=detail,
        ):
            self._sequencer_samples_logic.remove_sample(sample_id)

    def _submit_rename(self, sample_id: str, name: str) -> None:
        """Applies an inline rename, ignoring a blank name so the sample keeps its current one."""
        stripped = name.strip()
        if stripped:
            detail = self._history_detail.rename_sample(
                self._sequencer_samples_logic.sample_name(sample_id),
                stripped,
            )
            with self._history.transaction(
                HistoryAction.RENAME_SAMPLE,
                detail=detail,
            ):
                self._sequencer_samples_logic.rename_sample(sample_id, stripped)

    def _request_nes_frequency_change(self, nes_frequency: int) -> None:
        """Applies a NES-frequency change, confirming first when it would re-time existing samples.

        The rate governs how every sample plays back, so changing it on a project that already
        holds samples prompts once (until acknowledged for the session); an empty or acknowledged
        project applies silently. Cancelling restores the field to the project's current value.
        """
        if nes_frequency == self._sequencer_tracker_logic.settings.nes_frequency:
            return

        if self._nes_frequency_change_acknowledged or not self._project_controller.has_samples:
            self._perform_nes_frequency_change(nes_frequency)
            return

        self._dialogs.show_confirmation(
            tag=TAG_SEQUENCER_MODULE_DIALOG_NES_FREQUENCY,
            title=self._language_manager["global.dialog.title.change_nes_frequency"],
            message=self._language_manager["global.dialog.message.change_nes_frequency"],
            on_confirm=lambda: self._perform_nes_frequency_change(nes_frequency),
            ok_label=self._language_manager["global.dialog.label.change_and_retune"],
            opt_out_label=self._language_manager["global.dialog.label.dont_ask_again"],
            on_opt_out=self._acknowledge_nes_frequency_changes,
            on_cancel=self._sequencer_tracker_logic.push_settings,
        )

    def _perform_nes_frequency_change(self, nes_frequency: int) -> None:
        """Applies the rate as one undo entry, then requests a retune of the now-stale samples.

        The entry carries a rate-keyed coalesce target so the asynchronous per-sample retune
        results fold back into this same ``SET_NES_FREQUENCY`` entry: one undo restores both the
        prior rate and the prior reconstructions, and a later change to a different rate appends
        a fresh entry.
        """
        with self._history.transaction(
            HistoryAction.SET_NES_FREQUENCY,
            detail=self._history_detail.value(nes_frequency),
            coalesce=(nes_frequency,),
        ):
            self._sequencer_tracker_logic.set_nes_frequency(nes_frequency)

        self._on_nes_frequency_changed(nes_frequency)

    def nes_frequency_detail(self, nes_frequency: int) -> HistoryDetail:
        """The history detail for a NES-frequency change, so the retune can reuse its undo entry."""
        return self._history_detail.value(nes_frequency)

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
        self._settle_inserted_frame(position + 1)

    def _on_order_clone(self, position: int) -> None:
        self._sequencer_order_logic.clone_frame(position)
        self._settle_inserted_frame(position + 1)

    def _settle_inserted_frame(self, position: int) -> None:
        """Carries the playhead and the shown frame over a frame that has just been inserted.

        A frame arriving at ``position`` pushes every later frame one along, so a playhead
        standing on one of them follows it, and the grid moves to the new frame for the reader
        to work on.
        """
        self._relocate_playhead(
            lambda playhead: remap_after_insert(
                playhead,
                position,
            )
        )
        self._select_frame_when_idle(position)

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
        self._sequencer_tracker_logic.select_frame(to_position)

    def _on_order_play_from(self, position: int) -> None:
        """Plays from a frame: relocates the playhead when already playing, else starts there."""
        if self._song_player_logic.is_playing():
            self._song_player_logic.seek(position)
        else:
            self._song_player_logic.play_from(position)

    def _relocate_playhead(self, remap: Callable[[int], int]) -> None:
        """Keeps the live playhead on the frame it was sounding after a structural order edit.

        Both grids take the new position straight away, ahead of the worker's next row update, so
        rapid edits (e.g. a held Alt+arrow) stay in step, and a paused playhead — which reports no
        further rows — is marked on the frame the edit moved it to.
        """
        if self._playing_position is None:
            return

        order_position = remap(self._playing_position.order_position)
        if order_position == self._playing_position.order_position:
            return

        self._playing_position = SongPosition(
            order_position=order_position,
            row_index=self._playing_position.row_index,
        )
        self._song_player_logic.relocate(order_position)
        self._mark_playhead()

    def _select_frame_when_idle(self, frame_index: int) -> None:
        """Moves the editor selection to a frame, unless playback is actively driving it."""
        if not self._song_player_logic.is_playing():
            self._sequencer_tracker_logic.select_frame(frame_index)

    def _on_tracker_cell_focused(self) -> None:
        """Drops the order cursor and sample selection when the tracker tracker takes focus.

        The tracker, order, and samples panels each register a key-router scope active only while
        it holds a selection; keeping a single selection across the three lets only the focused
        panel consume keystrokes.
        """
        self._sequencer_order_panel.deselect_cell()
        self._sequencer_samples_panel.deselect()

    def _on_order_cell_focused(self) -> None:
        """Drops the tracker cursor and sample selection when the order tracker takes focus."""
        self._sequencer_tracker_panel.deselect_cell()
        self._sequencer_samples_panel.deselect()

    def create_tab(self) -> None:
        with dpg.tab(
            tag=TAG_GLOBAL_TAB_SEQUENCER,
            parent=TAG_GLOBAL_TABS,
            label=self._language_manager["global.menu.label.tab_sequencer"],
        ):
            self._side_panel_count = TabColumns.build(
                panel_gap=self._geometry.panel_gap,
                columns=[
                    ColumnSpec(
                        tag=_LEFT_COLUMN_TAG,
                        build=self._sequencer_browser_panel.create_panel,
                        theme=TAG_GLOBAL_THEME_PANEL_SURFACE,
                        width=self._geometry.side_width,
                        height=self._geometry.side_height,
                        no_scrollbar=True,
                    ),
                    ColumnSpec(
                        tag=_CENTER_COLUMN_TAG,
                        build=self._build_center_column,
                        theme=TAG_GLOBAL_THEME_PANEL_GROUND,
                        border=False,
                    ),
                    ColumnSpec(
                        tag=_RIGHT_COLUMN_TAG,
                        build=self._build_right_column,
                        theme=TAG_GLOBAL_THEME_PANEL_GROUND,
                        width=self._instruments_width,
                        height=self._right_height,
                        border=False,
                        no_scrollbar=True,
                    ),
                ],
            )

        self._sync_browser_width()

    def _build_center_column(self, parent: str) -> None:
        """Stacks the order table and tracker tracker down the centre column."""
        self._sequencer_order_panel.create_panel(parent)
        dpg.add_spacer(height=self._geometry.panel_gap, parent=parent)
        self._sequencer_tracker_panel.create_panel(parent)

    def _build_right_column(self, parent: str) -> None:
        """Stacks the module settings, samples, and history cards in the right column."""
        self._sequencer_module_panel.create_panel(parent)
        dpg.add_spacer(height=self._geometry.panel_gap)
        self._sequencer_samples_panel.create_panel(parent)
        dpg.add_spacer(height=self._geometry.panel_gap)
        self._sequencer_history_panel.create_panel(parent)
        self._sync_samples_height()

    @property
    def player(self) -> AudioPlayerProtocol:
        return self._guarded_player

    @property
    def edit_surfaces(self) -> Tuple[EditSurfaceProtocol, ...]:
        """The panels offering editing gestures on what they hold selected.

        The three hold one selection between them — a cursor in either grid, a row in the samples
        list — so the menu bar reaches whichever one has it.
        """
        return (
            self._sequencer_tracker_panel.edit_surface,
            self._sequencer_order_panel.edit_surface,
            self._sequencer_samples_panel,
        )
