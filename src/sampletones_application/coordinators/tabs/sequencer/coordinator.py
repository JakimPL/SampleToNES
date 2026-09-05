from pathlib import Path
from typing import Callable, Sequence, Tuple

from sampletones_application.categories.hierarchy import Tab
from sampletones_application.categories.instrument import InstrumentImportMessages
from sampletones_application.categories.manager import LanguageManager
from sampletones_application.config.managers.config import ConfigManager
from sampletones_application.config.managers.session import SessionManager
from sampletones_application.constants.playback import FollowMode
from sampletones_application.coordinators.edit.protocol import EditSurfaceProtocol
from sampletones_application.coordinators.export import InstrumentExportCoordinator
from sampletones_application.coordinators.original_audio import OriginalAudioLocator
from sampletones_application.coordinators.playback.guard import GuardedPlayer
from sampletones_application.coordinators.playback.protocol import AudioPlayerProtocol
from sampletones_application.coordinators.tabs.sequencer.blocks import SequencerBlocks
from sampletones_application.coordinators.tabs.sequencer.frames import SequencerFrames
from sampletones_application.coordinators.tabs.sequencer.history import SequencerHistoryRecorder
from sampletones_application.coordinators.tabs.sequencer.layout import SequencerTabLayout
from sampletones_application.coordinators.tabs.sequencer.playhead import SequencerPlayhead
from sampletones_application.coordinators.tabs.sequencer.project import OpenProjectRequirement
from sampletones_application.coordinators.tabs.sequencer.reconstructions import SequencerReconstructions
from sampletones_application.coordinators.tabs.sequencer.voices import SequencerVoices
from sampletones_application.logic.history.action import HistoryAction
from sampletones_application.logic.history.manager import HistoryManager
from sampletones_application.logic.project.controller import ProjectController
from sampletones_application.logic.reconstruction.browser.manager import BrowserManager
from sampletones_application.logic.sequencer.browser import SequencerBrowserLogic
from sampletones_application.logic.sequencer.channels import SequencerChannelsLogic
from sampletones_application.logic.sequencer.history_detail import (
    SequencerHistoryDetail,
)
from sampletones_application.logic.sequencer.order import (
    SequencerOrderLogic,
)
from sampletones_application.logic.sequencer.playback.song_player import SongPlayerLogic
from sampletones_application.logic.sequencer.playback.synthesizer import RowSynthesizer
from sampletones_application.logic.sequencer.tracker import (
    SequencerTrackerLogic,
    TrackerRegionAdjuster,
)
from sampletones_application.logic.sequencer.voices import SequencerVoicesLogic
from sampletones_application.logic.shared.file_playback import FilePlayback
from sampletones_application.logic.shared.tree import TreeLogic
from sampletones_application.parameters.sequencer import SequencerTabParameters
from sampletones_application.services.song_player.service import SongPlayerService
from sampletones_application.tags.sequencer import (
    TAG_SEQUENCER_BROWSER_PANEL,
    TAG_SEQUENCER_HISTORY_PANEL,
    TAG_SEQUENCER_MODULE_DIALOG_NES_FREQUENCY,
    TAG_SEQUENCER_MODULE_PANEL,
    TAG_SEQUENCER_ORDER_WINDOW_ORDER_CARD,
    TAG_SEQUENCER_TRACKER_PANEL,
    TAG_SEQUENCER_VOICES_PANEL,
)
from sampletones_application.ui.elements.status import GUIStatusBar
from sampletones_application.ui.panels.sequencer.browser import GUISequencerBrowserPanel
from sampletones_application.ui.panels.sequencer.history import GUISequencerHistoryPanel
from sampletones_application.ui.panels.sequencer.module import GUISequencerModulePanel
from sampletones_application.ui.panels.sequencer.order.panel import GUISequencerOrderPanel
from sampletones_application.ui.panels.sequencer.tracker.panel import GUISequencerTrackerPanel
from sampletones_application.ui.panels.sequencer.voices.panel import (
    GUISequencerVoicesPanel,
)
from sampletones_application.utils.gui.clipboard import SystemTextClipboard
from sampletones_application.utils.gui.dialogs import DialogsRenderer
from sampletones_application.utils.gui.frame import FrameCallbackManager
from sampletones_application.utils.gui.keyboard import ActivePredicate, KeyRouter
from sampletones_application.utils.gui.shortcuts.source import ShortcutSource
from sampletones_application.view_model.sequencer.channels import (
    SequencerChannelsViewModel,
)
from sampletones_application.view_model.sequencer.settings import (
    SequencerSettingsViewModel,
)
from sampletones_application.view_model.sequencer.song_player import SongPlayerViewModel
from sampletones_application.view_model.sequencer.voices import (
    SequencerVoicesViewModel,
)
from sampletones_application.view_model.shared.history import (
    HistoryDetail,
)
from sampletones_core.audio import AudioDeviceManager
from sampletones_core.constants.enums import ChannelName, FeatureKey
from sampletones_core.reconstructions import Reconstruction
from sampletones_core.structures.tree import FileSystemNode
from sampletones_shared.logger import logger
from sampletones_shared.types.callback import StringCallback, VoidCallback


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
        instrument_exports: InstrumentExportCoordinator,
        *,
        tab_active: ActivePredicate,
        layout: SequencerTabParameters,
        language_manager: LanguageManager,
        dialogs: DialogsRenderer,
        status_bar: GUIStatusBar,
        on_edit_voice_requested: StringCallback,
        on_favorite_changed: Callable[[FileSystemNode], None],
        on_sample_reconstruction_replaced: Callable[[str, Reconstruction], None],
        on_tab_switch: Callable[[Tab], None],
        on_nes_frequency_changed: Callable[[int], None],
        on_channels_changed: VoidCallback,
    ) -> None:
        self._project_controller = project_controller
        self._session_manager = session_manager
        self._history = history
        self._original_audio_locator = original_audio_locator
        self._instrument_exports = instrument_exports
        self._on_edit_voice_requested = on_edit_voice_requested
        self._on_favorite_changed = on_favorite_changed
        self._on_sample_reconstruction_replaced = on_sample_reconstruction_replaced
        self._on_tab_switch = on_tab_switch
        self._on_nes_frequency_changed = on_nes_frequency_changed
        self._on_channels_changed = on_channels_changed
        self._language_manager = language_manager
        self._dialogs = dialogs

        self._nes_frequency_change_acknowledged: bool = False

        self._sequencer_browser_logic: SequencerBrowserLogic = SequencerBrowserLogic(
            config_manager,
            browser_manager,
            project_controller,
        )
        self._file_playback: FilePlayback = FilePlayback(audio_device_manager)
        self._sequencer_tree_logic: TreeLogic = TreeLogic(
            session_manager,
            self._file_playback,
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
            initial_favorites_only=session_manager.is_favorites_filter_active(TAG_SEQUENCER_BROWSER_PANEL),
            initial_expanded_rows=session_manager.expanded_rows(TAG_SEQUENCER_BROWSER_PANEL),
        )
        self._sequencer_tracker_logic: SequencerTrackerLogic = SequencerTrackerLogic(project_controller)
        self._sequencer_order_logic: SequencerOrderLogic = SequencerOrderLogic(project_controller)
        self._blocks: SequencerBlocks = SequencerBlocks(
            self._sequencer_tracker_logic,
            self._sequencer_order_logic,
            project_controller,
            text_clipboard=SystemTextClipboard(),
        )
        self._tracker_region_adjuster: TrackerRegionAdjuster = TrackerRegionAdjuster(self._sequencer_tracker_logic)
        self._sequencer_voices_logic: SequencerVoicesLogic = SequencerVoicesLogic(
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
            channel_colors=layout.channel_colors,
            initial_collapsed=session_manager.is_card_collapsed(TAG_SEQUENCER_TRACKER_PANEL),
            initial_octave=session_manager.octave,
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
            channel_colors=layout.channel_colors,
            plus_minus_layout=layout.plus_minus,
            initial_collapsed=session_manager.is_card_collapsed(TAG_SEQUENCER_ORDER_WINDOW_ORDER_CARD),
            language_manager=language_manager,
            key_router=key_router,
            tab_active=tab_active,
            shortcut_source=shortcut_source,
        )
        self._sequencer_voices_panel: GUISequencerVoicesPanel = GUISequencerVoicesPanel(
            layout=layout.sequencer,
            detail_color=layout.muted_color,
            initial_collapsed=session_manager.is_card_collapsed(TAG_SEQUENCER_VOICES_PANEL),
            language_manager=language_manager,
            status_bar=status_bar,
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
        self._layout: SequencerTabLayout = SequencerTabLayout(
            self._sequencer_browser_panel,
            self._sequencer_order_panel,
            self._sequencer_tracker_panel,
            self._sequencer_module_panel,
            self._sequencer_voices_panel,
            self._sequencer_history_panel,
            layout=layout,
            session_manager=session_manager,
            language_manager=language_manager,
        )
        self._playhead: SequencerPlayhead = SequencerPlayhead(
            self._sequencer_tracker_panel,
            self._sequencer_order_panel,
        )
        self._frames: SequencerFrames = SequencerFrames(
            self._sequencer_order_logic,
            self._sequencer_tracker_logic,
            self._song_player_logic,
            project_controller,
            self._playhead,
        )
        self._open_project: OpenProjectRequirement = OpenProjectRequirement(
            project_controller,
            dialogs=dialogs,
            language_manager=language_manager,
        )
        self._history_detail: SequencerHistoryDetail = SequencerHistoryDetail(
            self._sequencer_tracker_logic,
            self._sequencer_voices_logic,
        )
        self._voices: SequencerVoices = SequencerVoices(
            self._sequencer_voices_logic,
            history,
            self._history_detail,
            project_controller,
            session_manager,
            self._open_project,
            dialogs=dialogs,
            language_manager=language_manager,
            import_messages=InstrumentImportMessages.build(language_manager),
            import_reconstruction=self.import_reconstruction,
        )
        self._reconstructions: SequencerReconstructions = SequencerReconstructions(
            self._sequencer_browser_logic,
            self._sequencer_tracker_logic,
            self._sequencer_voices_logic,
            self._sequencer_voices_panel,
            history,
            self._history_detail,
            project_controller,
            self._open_project,
            dialogs=dialogs,
            language_manager=language_manager,
            on_tab_switch=on_tab_switch,
            on_sample_reconstruction_replaced=on_sample_reconstruction_replaced,
        )
        self._recorder: SequencerHistoryRecorder = SequencerHistoryRecorder(
            history,
            project_controller,
            self._sequencer_tracker_logic,
            language_manager=language_manager,
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
        self._wire_voices_callbacks()
        self._wire_browser_callbacks()
        self._wire_playback_callbacks()
        self._wire_project_callbacks()
        self._wire_history()

    def _wire_collapse_handlers(self) -> None:
        for panel in (
            self._sequencer_order_panel,
            self._sequencer_tracker_panel,
            self._sequencer_module_panel,
            self._sequencer_voices_panel,
            self._sequencer_history_panel,
        ):
            panel.set_collapse_handler(self._layout.on_card_collapse_changed)

    def _wire_module_callbacks(self) -> None:
        self._sequencer_module_panel.on_nes_frequency = self._request_nes_frequency_change
        self._sequencer_module_panel.on_rows_per_pattern = self._recorder.undoable(
            HistoryAction.SET_ROWS_PER_PATTERN,
            self._sequencer_tracker_logic.set_rows_per_pattern,
            detail=self._history_detail.value,
            coalesce=self._recorder.module_setting_key,
        )
        self._sequencer_module_panel.on_tempo = self._recorder.undoable(
            HistoryAction.SET_TEMPO,
            self._sequencer_tracker_logic.set_tempo,
            detail=self._history_detail.value,
            coalesce=self._recorder.module_setting_key,
        )
        self._sequencer_module_panel.on_speed = self._recorder.undoable(
            HistoryAction.SET_SPEED,
            self._sequencer_tracker_logic.set_speed,
            detail=self._history_detail.value,
            coalesce=self._recorder.module_setting_key,
        )

    def _wire_tracker_callbacks(self) -> None:
        self._sequencer_tracker_panel.on_clear_row = self._recorder.undoable(
            HistoryAction.CLEAR_ROW,
            self._sequencer_tracker_logic.clear_cell,
            detail=self._history_detail.clear_row,
        )
        self._sequencer_tracker_panel.on_clear_subcolumn = self._recorder.undoable(
            HistoryAction.CLEAR_SUBCOLUMN,
            self._sequencer_tracker_logic.clear_cell_subcolumn,
            detail=self._history_detail.clear_subcolumn,
        )
        self._sequencer_tracker_panel.on_set_row = self._recorder.undoable(
            HistoryAction.EDIT_ROW,
            self._sequencer_tracker_logic.write_cell,
            detail=self._history_detail.edit_row,
            coalesce=self._recorder.edit_row_key,
        )
        self._sequencer_tracker_panel.on_set_note_off = self._recorder.undoable(
            HistoryAction.NOTE_OFF,
            self._sequencer_tracker_logic.cut_note,
            detail=self._history_detail.note_off,
            coalesce=self._recorder.cell_key,
        )
        self._sequencer_tracker_panel.on_note_typed = self._recorder.undoable(
            HistoryAction.EDIT_ROW,
            self._sequencer_tracker_logic.write_note,
            detail=self._history_detail.note_typed,
            coalesce=self._recorder.note_key,
        )
        self._sequencer_tracker_panel.on_octave_changed = self._session_manager.set_octave
        self._sequencer_tracker_panel.on_cell_selected = self._on_tracker_cell_focused
        self._sequencer_tracker_panel.on_play_from_row = self._on_tracker_play_from_row
        self._sequencer_tracker_panel.on_play_from_frame = self.play_from_current_frame
        self._sequencer_tracker_panel.on_adjust_transpose = self._recorder.undoable(
            HistoryAction.ADJUST_TRANSPOSE,
            self._tracker_region_adjuster.adjust_transpose,
            detail=self._history_detail.adjust_transpose,
            coalesce=self._recorder.adjustment_key,
        )
        self._sequencer_tracker_panel.on_adjust_volume = self._recorder.undoable(
            HistoryAction.ADJUST_VOLUME,
            self._tracker_region_adjuster.adjust_volume,
            detail=self._history_detail.adjust_volume,
            coalesce=self._recorder.adjustment_key,
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

    def toggle_channel(self, channel: ChannelName) -> None:
        """Flips one channel between audible and silent, the menu's per-channel gesture."""
        self._sequencer_channels_logic.toggle(channel)

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
        self._sequencer_order_panel.on_frame_selected = self._frames.select
        self._sequencer_order_panel.on_remove_requested = self._recorder.undoable(
            HistoryAction.REMOVE_FRAME,
            self._frames.remove,
            detail=self._history_detail.remove_frame,
        )
        self._sequencer_order_panel.on_duplicate_requested = self._recorder.undoable(
            HistoryAction.DUPLICATE_FRAME,
            self._frames.duplicate,
            detail=self._history_detail.copy_frame,
        )
        self._sequencer_order_panel.on_clone_requested = self._recorder.undoable(
            HistoryAction.CLONE_FRAME,
            self._frames.clone,
            detail=self._history_detail.copy_frame,
        )
        self._sequencer_order_panel.on_insert_requested = self._recorder.undoable(
            HistoryAction.ADD_FRAME,
            self._frames.insert,
            detail=self._history_detail.add_frame,
        )
        self._sequencer_order_panel.on_clear_requested = self._recorder.undoable(
            HistoryAction.CLEAR_FRAME,
            self._frames.clear,
            detail=self._history_detail.clear_frame,
        )
        self._sequencer_order_panel.on_play_from_requested = self._frames.play_from
        self._sequencer_order_panel.on_move_requested = self._recorder.undoable(
            HistoryAction.MOVE_FRAME,
            self._frames.move,
            detail=self._history_detail.move_frame,
        )
        self._sequencer_order_panel.on_set_order_entry = self._recorder.undoable(
            HistoryAction.SET_ORDER_ENTRY,
            self._sequencer_order_logic.set_order_entry,
            detail=self._history_detail.set_order_entry,
        )
        self._sequencer_order_panel.on_set_master_entry = self._recorder.undoable(
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
        self._sequencer_tracker_panel.can_paste_block = self._blocks.can_paste_tracker
        self._sequencer_order_panel.can_paste_block = self._blocks.can_paste_order
        self._sequencer_tracker_panel.on_copy_block = self._blocks.copy_tracker
        self._sequencer_tracker_panel.on_cut_block = self._recorder.undoable(
            HistoryAction.CUT_BLOCK,
            self._blocks.cut_tracker,
            detail=self._history_detail.tracker_block,
        )
        self._sequencer_tracker_panel.on_delete_block = self._recorder.undoable(
            HistoryAction.DELETE_BLOCK,
            self._blocks.clear_tracker,
            detail=self._history_detail.tracker_block,
        )
        self._sequencer_tracker_panel.on_paste_block = self._recorder.undoable(
            HistoryAction.PASTE_BLOCK,
            self._blocks.paste_tracker,
            detail=self._history_detail.tracker_paste,
        )
        self._sequencer_order_panel.on_copy_block = self._blocks.copy_order
        self._sequencer_order_panel.on_cut_block = self._recorder.undoable(
            HistoryAction.CUT_BLOCK,
            self._blocks.cut_order,
            detail=self._history_detail.order_block,
        )
        self._sequencer_order_panel.on_delete_block = self._recorder.undoable(
            HistoryAction.DELETE_BLOCK,
            self._blocks.clear_order,
            detail=self._history_detail.order_block,
        )
        self._sequencer_order_panel.on_paste_block = self._recorder.undoable(
            HistoryAction.PASTE_BLOCK,
            self._blocks.paste_order,
            detail=self._history_detail.order_paste,
        )

    def _wire_voices_callbacks(self) -> None:
        self._sequencer_voices_logic.on_voices_changed = self._on_voices_changed
        self._sequencer_voices_logic.on_edit_voice_requested = self._dispatch_edit_voice
        self._sequencer_voices_logic.on_autoplay_error = self._on_preview_error
        self._sequencer_voices_panel.voice_footprint = self._sequencer_voices_logic.build_voice_footprint
        self._sequencer_voices_panel.on_voice_selected = self._on_voice_selected
        self._sequencer_voices_panel.on_voice_edit_requested = self._sequencer_voices_logic.request_edit
        self._sequencer_voices_panel.on_remove_requested = self._voices.remove
        self._sequencer_voices_panel.on_play_requested = self._sequencer_voices_logic.play_voice
        self._sequencer_voices_panel.on_move_requested = self._recorder.undoable(
            HistoryAction.MOVE_VOICE,
            self._sequencer_voices_logic.move_voice,
            detail=self._history_detail.move_voice,
        )
        self._sequencer_voices_panel.on_rename_committed = self._voices.submit_rename
        self._sequencer_voices_panel.on_duplicate_requested = self._recorder.undoable(
            HistoryAction.DUPLICATE_VOICE,
            self._sequencer_voices_logic.duplicate_voice,
            detail=self._history_detail.duplicate_voice,
        )
        self._sequencer_voices_panel.on_new_instrument_requested = self.add_instrument
        self._sequencer_voices_panel.on_add_sample_requested = self.add_sample_from_file
        self._sequencer_voices_panel.on_import_instrument_requested = self.import_instrument
        self._sequencer_voices_panel.voice_instruments = self._instrument_exports.voice_instruments
        self._sequencer_voices_panel.on_export_instrument_requested = self._instrument_exports.request_voice
        self._sequencer_voices_panel.instrument_channels = self._sequencer_voices_logic.instrument_channels
        self._sequencer_voices_panel.on_instrument_from_channel_requested = self.add_instrument_from_channel

    def _wire_browser_callbacks(self) -> None:
        self._sequencer_browser_panel.set_collapse_handler(self._layout.on_browser_collapse_changed)
        self._sequencer_browser_panel.on_favorites_filter_changed = self._layout.on_browser_favorites_filter_changed
        self._sequencer_browser_panel.on_add_to_sequencer = self.import_reconstruction
        self._sequencer_browser_panel.can_add_to_sequencer = self._is_project_open
        self._sequencer_browser_panel.on_replace_in_sequencer = self.replace_reconstruction
        self._sequencer_browser_panel.replace_in_sequencer_label = self._reconstructions.replace_target_label
        self._sequencer_browser_panel.on_locate_original_audio = self._original_audio_locator.locate
        self._sequencer_browser_panel.on_refresh_tree = self._sequencer_browser_logic.refresh_tree
        self._sequencer_tree_logic.on_lock_state_changed = self._sequencer_browser_panel.set_tree_enabled
        self._sequencer_tree_logic.on_favorite_changed = self._on_favorite_changed
        self._sequencer_tree_logic.on_search_update_needed = self._sequencer_browser_panel.update_tree_visibility
        self._file_playback.on_error = self._on_preview_error

    def _wire_playback_callbacks(self) -> None:
        self._song_player_logic.on_position_changed = self._on_player_position_changed
        self._song_player_logic.on_view_changed = self._on_player_view_changed
        self._song_player_logic.on_error = self._on_player_error

    def _wire_project_callbacks(self) -> None:
        self._project_controller.on_settings_changed = self._sequencer_tracker_logic.push_settings
        self._project_controller.on_song_changed = self._on_song_changed
        self._project_controller.on_voices_changed = self._sequencer_voices_logic.push_voices
        self._project_controller.on_project_replaced = self._on_project_replaced

    def _wire_history(self) -> None:
        self._sequencer_history_panel.on_undo = self.undo
        self._sequencer_history_panel.on_redo = self.redo
        self._sequencer_history_panel.on_jump_to = self.jump_to_history

    def _on_settings_changed(
        self,
        view_model: SequencerSettingsViewModel,
    ) -> None:
        """Hands the project's song settings to the two panels that read them.

        The module panel shows the timing fields themselves; the tracker reads the meter out of
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
        self._frames.play_from(self._sequencer_tracker_logic.frame_index)

    def add_instrument(self) -> None:
        """Appends a hand-written voice to the pool, the menu bar's entry to the gesture."""
        self._voices.add_instrument()

    def add_instrument_from_channel(
        self,
        voice_id: str,
        channel_name: ChannelName,
    ) -> None:
        """Takes what one channel of a voice plays as an instrument of its own, then opens it.

        Args:
            voice_id: The voice the channel belongs to.
            channel_name: The channel whose envelopes the instrument takes.
        """
        self._voices.add_instrument_from_channel(voice_id, channel_name)

    def add_sample_from_file(self) -> None:
        """Brings a reconstruction saved anywhere on disk into the pool as a sample."""
        self._voices.add_sample_from_file()

    def import_instrument(self) -> None:
        """Brings a FamiTracker instrument file into the pool as an instrument voice."""
        self._voices.import_instrument()

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
        self._sequencer_history_panel.update_view(self._recorder.view_model())

    def reconstruction_edit_detail(
        self,
        voice_id: str,
        channel_name: ChannelName,
        feature_key: FeatureKey,
    ) -> HistoryDetail:
        """Describes a reconstruction edit for the project history's detail line."""
        return self._history_detail.edit_reconstruction(
            voice_id,
            channel_name,
            feature_key,
        )

    def instrument_edit_detail(
        self,
        voice_id: str,
        feature_key: FeatureKey,
    ) -> HistoryDetail:
        """Describes a hand-written voice's edited dimension for the project history."""
        return self._history_detail.edit_instrument(voice_id, feature_key)

    def reconstruction_stem_detail(
        self,
        voice_id: str,
        stem_name: str,
    ) -> HistoryDetail:
        """Describes a recording taken out of a reconstruction for the project history."""
        return self._history_detail.remove_stem(voice_id, stem_name)

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
        self._sequencer_voices_logic.push_voices()
        self._sequencer_channels_logic.push_channels()
        is_open = self._project_controller.is_open
        self._sequencer_module_panel.set_enabled(is_open)
        self._sequencer_tracker_panel.set_enabled(is_open)
        self._sequencer_order_panel.set_enabled(is_open)
        self._sequencer_history_panel.set_enabled(is_open)

    def repaint(self) -> None:
        """Draws every table again so its tints take the palette now in place.

        DearPyGui keeps a table's row, column and cell tints as state of the table rather than
        as a property of an item, so they take a new color by being issued again. Each panel
        answers for the tints it owns, and this is where the palette asks all three.
        """
        self._sequencer_tracker_panel.repaint()
        self._sequencer_order_panel.repaint()
        self._sequencer_voices_panel.repaint()

    def refresh_browser(self) -> None:
        self._sequencer_browser_panel.refresh()

    def save_browser_shape(self) -> None:
        """Writes down the rows the browser stands open, so a later run brings them back."""
        self._session_manager.set_expanded_rows(
            self._sequencer_browser_panel.tag,
            self._sequencer_browser_panel.expanded_rows,
        )

    def repaint_browser_favorites(self, nodes: Sequence[FileSystemNode]) -> None:
        self._sequencer_browser_panel.update_favorite_indicators(nodes)

    def _on_song_changed(self) -> None:
        self._sequencer_tracker_logic.push_settings()
        self._sequencer_tracker_logic.push_tracker()
        self._sequencer_order_logic.push_order()

    def _on_player_error(self, error: Exception) -> None:
        self._dialogs.show_error(error)

    def _on_player_view_changed(self, view_model: SongPlayerViewModel) -> None:
        """Settles the marks the transport owns, and how far the grid chases the playhead.

        The player emits a view on every position update and on every change to the setting, so
        reading the follow behavior here keeps the grid in step both while a song sounds and the
        moment the reader picks another mode.
        """
        self._sequencer_tracker_panel.set_row_following(view_model.follow_mode.follows_row)
        if not view_model.is_playing and not view_model.is_paused:
            self._playhead.stop()

    def _on_player_position_changed(
        self,
        order_position: int,
        row_index: int,
    ) -> None:
        """Moves the marks the playhead carries, showing the frame it sounds when following.

        The frame is selected ahead of the marks so the row's mark, and the scroll that reveals it,
        land on the pattern the playhead has reached.
        """
        self._playhead.stand_at(order_position, row_index)
        if self._song_player_logic.follow_mode.follows_pattern:
            self._sequencer_tracker_logic.select_frame(order_position)

        self._playhead.mark()

    def _on_preview_error(self, exception: Exception) -> None:
        FrameCallbackManager.set_frame_callback(lambda: self._dialogs.show_error(exception))

    def _is_project_open(self) -> bool:
        return self._project_controller.is_open

    def import_reconstruction(self, filepath: Path) -> None:
        """Brings a reconstruction file into the pool as a sample."""
        self._reconstructions.import_from_file(filepath)

    def import_reconstruction_object(self, reconstruction: Reconstruction, name: str) -> None:
        """Adds an in-memory reconstruction — the one open in the Reconstruction tab — as a sample."""
        self._reconstructions.import_object(reconstruction, name)

    def replace_reconstruction(self, filepath: Path) -> None:
        """Substitutes the selected sample's reconstruction with a browser file's."""
        self._reconstructions.replace_from_file(filepath)

    def _dispatch_edit_voice(self, voice_id: str) -> None:
        self._on_edit_voice_requested(voice_id)

    def _on_tracker_play_from_row(self, row_index: int) -> None:
        """Starts playback from the right-clicked row of the frame the tracker is showing."""
        self._song_player_logic.play_from(
            self._sequencer_tracker_logic.frame_index,
            row_index,
        )

    def _on_voices_changed(
        self,
        view_model: SequencerVoicesViewModel,
    ) -> None:
        self._sequencer_voices_panel.update_view(view_model)
        self._sequencer_tracker_panel.update_samples(view_model)

    def _on_voice_selected(self, voice_id: str) -> None:
        self._sequencer_tracker_panel.deselect_cell()
        self._sequencer_order_panel.deselect_cell()
        self._sequencer_voices_logic.request_autoplay(voice_id)
        logger.debug(f"Sequencer sample selected: {voice_id}")

    def _request_nes_frequency_change(self, nes_frequency: int) -> None:
        """Applies a NES-frequency change, confirming first when it would re-time existing samples.

        The rate governs how every sample plays back, so changing it on a project that already
        holds samples prompts once (until acknowledged for the session); an empty or acknowledged
        project applies silently. Cancelling restores the field to the project's current value.
        """
        if nes_frequency == self._sequencer_tracker_logic.settings.nes_frequency:
            return

        if self._nes_frequency_change_acknowledged or not self._project_controller.has_voices:
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

    def _on_tracker_cell_focused(self) -> None:
        """Drops the order cursor and sample selection when the tracker tracker takes focus.

        The tracker, order, and samples panels each register a key-router scope active only while
        it holds a selection; keeping a single selection across the three lets only the focused
        panel consume keystrokes.
        """
        self._sequencer_order_panel.deselect_cell()
        self._sequencer_voices_panel.deselect()

    def _on_order_cell_focused(self) -> None:
        """Drops the tracker cursor and sample selection when the order tracker takes focus."""
        self._sequencer_tracker_panel.deselect_cell()
        self._sequencer_voices_panel.deselect()

    def create_tab(self) -> None:
        """Builds this tab, which the layout holds and refits from here on."""
        self._layout.create_tab()

    def sync_responsive_layout(self) -> None:
        """Refits this tab's columns to the current viewport, the entry the resize handler calls."""
        self._layout.sync_responsive_layout()

    @property
    def player(self) -> AudioPlayerProtocol:
        return self._guarded_player

    def build_voice_actions(self) -> None:
        """States the chosen voice's actions into the menu being built, for the bar's Voice group."""
        self._sequencer_voices_panel.build_voice_actions()

    @property
    def edit_surfaces(self) -> Tuple[EditSurfaceProtocol, ...]:
        """The panels offering editing gestures on what they hold selected.

        The three hold one selection between them — a cursor in either grid, a row in the samples
        list — so the menu bar reaches whichever one has it.
        """
        return (
            self._sequencer_tracker_panel.edit_surface,
            self._sequencer_order_panel.edit_surface,
            self._sequencer_voices_panel,
        )
