from functools import partial
from pathlib import Path
from typing import Callable, Dict, Mapping, Optional, Sequence, Tuple

import dearpygui.dearpygui as dpg

from sampletones_application.categories.manager import LanguageManager
from sampletones_application.config.managers.config import ConfigManager
from sampletones_application.config.managers.session import SessionManager
from sampletones_application.coordinators.export.instrument import (
    InstrumentExportCoordinator,
)
from sampletones_application.coordinators.export.setup import ExportSetup
from sampletones_application.coordinators.original_audio import OriginalAudioLocator
from sampletones_application.coordinators.playback.failures import PlaybackFailurePresenter
from sampletones_application.coordinators.playback.guard import GuardedPlayer
from sampletones_application.coordinators.playback.protocol import AudioPlayerProtocol
from sampletones_application.coordinators.tabs.columns import fit_side_column, persisting_collapse, side_column
from sampletones_application.coordinators.tabs.reconstruction.exports import ReconstructionExports
from sampletones_application.coordinators.tabs.reconstruction.loading import ReconstructionLoading
from sampletones_application.coordinators.tabs.reconstruction.removals import ReconstructionRemovals
from sampletones_application.logic.history.manager import HistoryManager
from sampletones_application.logic.project.controller import ProjectController
from sampletones_application.logic.reconstruction.audition import (
    InstrumentAuditionLogic,
)
from sampletones_application.logic.reconstruction.browser.logic import BrowserLogic
from sampletones_application.logic.reconstruction.browser.manager import BrowserManager
from sampletones_application.logic.reconstruction.editor import (
    InstrumentEditDetail,
    InstrumentEditor,
)
from sampletones_application.logic.reconstruction.instruments import (
    PendingChangesProtocol,
    ReconstructionInstrumentsLogic,
)
from sampletones_application.logic.reconstruction.keys import KeyArming, ReconstructionKeys
from sampletones_application.logic.reconstruction.manager import ReconstructionManager
from sampletones_application.logic.reconstruction.reconstruction import (
    ReconstructionPanelLogic,
)
from sampletones_application.logic.reconstruction.rewrites.steps import (
    ListeningChange,
    RateChange,
    Rewrite,
)
from sampletones_application.logic.shared.audio_player import AudioPlayer
from sampletones_application.logic.shared.file_playback import FilePlayback
from sampletones_application.logic.shared.live import LiveKeysLogic
from sampletones_application.logic.shared.player import PlayerLogic
from sampletones_application.logic.shared.preview_player import PreviewPlayer
from sampletones_application.logic.shared.previews import DocumentPreviews
from sampletones_application.logic.shared.tree import TreeLogic
from sampletones_application.parameters.reconstruction import (
    ReconstructionTabParameters,
)
from sampletones_application.services.export.service import ExportService
from sampletones_application.tags.compose import compose_tag
from sampletones_application.tags.general import (
    SUF_PANEL_CENTER,
    SUF_PANEL_LEFT,
    SUF_PANEL_RIGHT,
    TAG_GLOBAL_TAB_RECONSTRUCTION,
    TAG_GLOBAL_TABS,
    TAG_GLOBAL_THEME_PANEL_GROUND,
)
from sampletones_application.tags.reconstructions import (
    TAG_RECONSTRUCTIONS_BROWSER_PANEL,
    TAG_RECONSTRUCTIONS_INSTRUMENTS_PANEL,
    TAG_RECONSTRUCTIONS_RECONSTRUCTION_PANEL_AUDIO,
    TAG_RECONSTRUCTIONS_RECONSTRUCTION_PANEL_PLOT,
    TAG_RECONSTRUCTIONS_RECONSTRUCTION_PANEL_STEMS,
)
from sampletones_application.ui.elements.layout.columns import ColumnSpec, TabColumns
from sampletones_application.ui.elements.status import GUIStatusBar
from sampletones_application.ui.panels.reconstruction.audio import (
    GUIReconstructionAudioPanel,
)
from sampletones_application.ui.panels.reconstruction.browser import (
    GUIReconstructionsBrowserPanel,
)
from sampletones_application.ui.panels.reconstruction.instruments.instruments import (
    GUIReconstructionInstrumentsPanel,
)
from sampletones_application.ui.panels.reconstruction.plot import (
    GUIReconstructionPlotPanel,
)
from sampletones_application.ui.panels.reconstruction.stems import (
    GUIReconstructionStemsPanel,
)
from sampletones_application.utils.callbacks.gates import Wait, gated
from sampletones_application.utils.gui.dialogs import DialogsRenderer
from sampletones_application.utils.gui.keyboard import PRIORITY_PANEL, ActivePredicate, KeyRouter
from sampletones_application.utils.midi import MidiRouter
from sampletones_application.view_model.reconstruction.reconstruction import (
    ReconstructionViewModel,
)
from sampletones_application.view_model.reconstruction.work import Work
from sampletones_application.view_model.shared.audio_data import AudioData
from sampletones_application.view_model.shared.recording import NamedRecordingViewModel
from sampletones_core.audio.output import AudioOutput
from sampletones_core.constants.audio import START_OF_AUDIO
from sampletones_core.constants.enums import ChannelName
from sampletones_core.exports.backend import ExportBackend
from sampletones_core.exports.format import ExportFormat
from sampletones_core.structures.tree import FileSystemNode
from sampletones_shared.types.callback import PathCallback, VoidCallback

_LEFT_COLUMN_TAG = compose_tag(TAG_GLOBAL_TAB_RECONSTRUCTION, SUF_PANEL_LEFT)
_CENTER_COLUMN_TAG = compose_tag(TAG_GLOBAL_TAB_RECONSTRUCTION, SUF_PANEL_CENTER)
_RIGHT_COLUMN_TAG = compose_tag(TAG_GLOBAL_TAB_RECONSTRUCTION, SUF_PANEL_RIGHT)


class ReconstructionTabCoordinator:
    def __init__(
        self,
        config_manager: ConfigManager,
        session_manager: SessionManager,
        output: AudioOutput,
        preview_player: PreviewPlayer,
        reconstruction_manager: ReconstructionManager,
        project_controller: ProjectController,
        browser_manager: BrowserManager,
        export_service: ExportService,
        export_backends: Dict[ExportFormat, ExportBackend],
        format_setups: Mapping[ExportFormat, ExportSetup],
        on_load_reconstruction_with_confirmation: Callable[[Optional[Path]], None],
        on_change_audio_state: VoidCallback,
        on_favorite_changed: Callable[[FileSystemNode], None],
        on_rewrite_requested: Callable[[Rewrite], None],
        pending_changes: PendingChangesProtocol,
        after_edits: Wait,
        original_audio_locator: OriginalAudioLocator,
        instrument_exports: InstrumentExportCoordinator,
        history: HistoryManager,
        instrument_edit_detail: InstrumentEditDetail,
        previews: DocumentPreviews,
        *,
        key_router: KeyRouter,
        midi_router: MidiRouter,
        live_keys: LiveKeysLogic,
        sample_root: int,
        tab_active: ActivePredicate,
        layout: ReconstructionTabParameters,
        language_manager: LanguageManager,
        dialogs: DialogsRenderer,
        playback_failures: PlaybackFailurePresenter,
        status_bar: GUIStatusBar,
    ) -> None:
        self._language_manager = language_manager
        self._instrument_editor: InstrumentEditor = InstrumentEditor(
            reconstruction_manager,
            project_controller,
            history,
            instrument_edit_detail,
        )
        self._session_manager = session_manager
        self._playback_failures = playback_failures
        self._original_audio_locator = original_audio_locator
        self._on_rewrite_requested = on_rewrite_requested

        self._geometry = layout.geometry
        self._side_panel_count: int
        self._instruments_width = layout.right_column_width
        self._right_height = layout.right_column_height
        self._loading = ReconstructionLoading(
            reconstruction_manager,
            dialogs=dialogs,
            language_manager=language_manager,
        )

        self._browser_logic: BrowserLogic = BrowserLogic(
            config_manager,
            browser_manager,
        )
        self._file_playback: FilePlayback = FilePlayback(preview_player, previews)
        self._browser_tree_logic: TreeLogic = TreeLogic(
            session_manager,
            self._file_playback,
            scheduling=layout.scheduling,
        )
        self._browser_panel: GUIReconstructionsBrowserPanel = GUIReconstructionsBrowserPanel(
            self._browser_logic.tree,
            self._browser_tree_logic,
            scheduling=layout.scheduling,
            language_manager=language_manager,
            status_bar=status_bar,
            colors=layout.tree_colors,
            stem_colors=layout.stem_colors,
            initial_collapsed=session_manager.is_card_collapsed(TAG_RECONSTRUCTIONS_BROWSER_PANEL),
            initial_favorites_only=session_manager.is_favorites_filter_active(TAG_RECONSTRUCTIONS_BROWSER_PANEL),
            initial_expanded_rows=session_manager.expanded_rows(TAG_RECONSTRUCTIONS_BROWSER_PANEL),
        )
        self._browser_panel.on_recordings_requested = self._on_browser_recordings_requested
        self._browser_tree_logic.on_lock_state_changed = self._browser_panel.set_tree_enabled
        self._browser_tree_logic.on_favorite_changed = on_favorite_changed
        self._browser_tree_logic.on_search_update_needed = self._browser_panel.update_tree_visibility
        self._file_playback.on_error = self._playback_failures.present_later
        self._browser_panel.set_collapse_handler(
            persisting_collapse(self._session_manager, then=self._sync_browser_width)
        )
        self._browser_panel.on_favorites_filter_changed = self._session_manager.set_favorites_filter_active
        self._reconstruction_player_logic = PlayerLogic(
            AudioPlayer(output),
            on_change_audio_state,
        )
        self._reconstruction_player_logic.on_error = playback_failures.present_playing_failure
        self._guarded_player = GuardedPlayer(
            self._reconstruction_player_logic,
            failures=playback_failures,
            previews=previews,
        )
        self._reconstruction_audio_panel: GUIReconstructionAudioPanel = GUIReconstructionAudioPanel(
            path_colors=layout.path_colors,
            path_status_color=layout.path_status_color,
            initial_collapsed=session_manager.is_card_collapsed(TAG_RECONSTRUCTIONS_RECONSTRUCTION_PANEL_AUDIO),
            language_manager=language_manager,
            status_bar=status_bar,
        )
        self._reconstruction_plot_panel: GUIReconstructionPlotPanel = GUIReconstructionPlotPanel(
            layout_graphs=layout.graphs,
            channel_colors=layout.channel_colors,
            stem_colors=layout.stem_colors,
            initial_collapsed=session_manager.is_card_collapsed(TAG_RECONSTRUCTIONS_RECONSTRUCTION_PANEL_PLOT),
            language_manager=language_manager,
            status_bar=status_bar,
        )
        self._reconstruction_stems_panel: GUIReconstructionStemsPanel = GUIReconstructionStemsPanel(
            stems_layout=layout.stems,
            stem_colors=layout.stem_colors,
            language_manager=language_manager,
            status_bar=status_bar,
            initial_collapsed=session_manager.is_card_collapsed(TAG_RECONSTRUCTIONS_RECONSTRUCTION_PANEL_STEMS),
        )
        for card in (
            self._reconstruction_audio_panel,
            self._reconstruction_plot_panel,
            self._reconstruction_stems_panel,
        ):
            card.set_collapse_handler(persisting_collapse(self._session_manager, then=None))
        self._reconstruction_player_logic.on_position_changed = self._reconstruction_plot_panel.set_playback_position
        self._reconstruction_plot_panel.on_position_clicked = self._play_from
        self._reconstruction_panel_logic: ReconstructionPanelLogic = ReconstructionPanelLogic(
            session_manager,
            reconstruction_manager,
            export_service,
            export_backends,
        )
        self._exports = ReconstructionExports(
            self._reconstruction_panel_logic,
            self._instrument_editor,
            instrument_exports,
            export_backends,
            format_setups,
            dialogs=dialogs,
            language_manager=language_manager,
        )
        self._removals = ReconstructionRemovals(
            reconstruction_manager,
            self._browser_logic,
            self._browser_panel,
            self._reconstruction_stems_panel,
            dialogs=dialogs,
            language_manager=language_manager,
            on_rewrite_requested=on_rewrite_requested,
            on_document_detached=self.update_reconstruction,
        )
        self._reconstruction_instruments_panel: GUIReconstructionInstrumentsPanel = GUIReconstructionInstrumentsPanel(
            pitch_stepper_style=layout.pitch_stepper_style,
            copy_width=layout.copy_width,
            feature_colors=layout.feature_colors,
            stem_colors=layout.stem_colors,
            layout_graphs=layout.graphs,
            language_manager=language_manager,
            status_bar=status_bar,
            key_router=key_router,
            tab_active=tab_active,
            initial_collapsed=session_manager.is_card_collapsed(TAG_RECONSTRUCTIONS_INSTRUMENTS_PANEL),
        )
        self._reconstruction_instruments_panel.set_collapse_handler(
            persisting_collapse(self._session_manager, then=self._sync_instruments_width)
        )
        self._reconstruction_instruments_logic: ReconstructionInstrumentsLogic = ReconstructionInstrumentsLogic(
            self._instrument_editor,
            pending_changes,
        )
        self._instrument_audition_logic: InstrumentAuditionLogic = InstrumentAuditionLogic(
            self._instrument_editor,
            project_controller,
        )
        self._key_arming: KeyArming = KeyArming(
            self._instrument_editor,
            self._instrument_audition_logic,
            reconstruction_manager,
            project_controller,
            session_manager,
            sample_root=sample_root,
        )
        self._reconstruction_keys: ReconstructionKeys = ReconstructionKeys(
            self._key_arming,
            live_keys,
            session_manager,
            follower=self._follow_key,
        )
        midi_router.register(
            self._reconstruction_keys,
            priority=PRIORITY_PANEL,
            active=lambda: tab_active() and not key_router.is_modal_open,
        )

        self._browser_panel.on_refresh_tree = self._browser_logic.refresh_tree
        self._browser_panel.on_load_reconstruction = on_load_reconstruction_with_confirmation
        self._browser_panel.on_reconstruction_remove_requested = self._removals.request_reconstruction
        self._browser_panel.on_directory_remove_requested = self._removals.request_directory

        self._reconstruction_audio_panel.on_audio_source_changed = self._reconstruction_panel_logic.set_audio_source
        self._reconstruction_audio_panel.on_nes_frequency_changed = self._request_rate_change
        self._reconstruction_plot_panel.on_channels_changed = self._reconstruction_panel_logic.set_selected_channels
        self._reconstruction_stems_panel.on_stem_channels_changed = self._reconstruction_panel_logic.set_stem_channels
        self._reconstruction_stems_panel.on_stem_solo_requested = self._reconstruction_panel_logic.solo_stem
        self._reconstruction_stems_panel.on_stem_remove_requested = self._removals.request_stem
        self._browser_panel.on_locate_original_audio = self._original_audio_locator.locate

        self._reconstruction_panel_logic.on_view_changed = self._update_reconstruction_view
        self._reconstruction_panel_logic.on_stems_view_changed = self._reconstruction_stems_panel.update_view
        self._reconstruction_panel_logic.on_ownership_changed = self._reconstruction_plot_panel.update_ownership
        self._reconstruction_panel_logic.on_listening_changed = self._reconstruction_instruments_logic.follow_listening
        self._reconstruction_panel_logic.on_audio_data_changed = self._on_audio_data_changed
        self._reconstruction_panel_logic.on_waveform_load_changed = self._reconstruction_plot_panel.load_waveform_data
        self._reconstruction_panel_logic.on_waveform_update_changed = (
            self._reconstruction_plot_panel.update_waveform_data
        )
        self._reconstruction_panel_logic.on_waveform_cleared = self._reconstruction_plot_panel.clear_waveform
        self._reconstruction_panel_logic.on_renders_wanted = self._request_listening
        self._reconstruction_panel_logic.on_waveform_source_changed = (
            self._reconstruction_plot_panel.set_waveform_top_source
        )
        self._reconstruction_panel_logic.on_open_export_instruments_dialog = self._exports.open_instruments_dialog
        self._reconstruction_panel_logic.on_open_export_wav_dialog = self._exports.open_wav_dialog
        self._reconstruction_panel_logic.on_export_dropped = self._exports.report_dropped
        self._reconstruction_panel_logic.on_locate_audio_not_found = lambda path: dialogs.show_file_not_found(
            path,
            language_manager["reconstructions.reconstruction.message.locate_audio_failed"],
        )

        export_service.subscribe(self._exports.report)

        self._reconstruction_instruments_logic.on_view_changed = self._reconstruction_instruments_panel.update_view
        self._reconstruction_instruments_logic.on_feature_data_changed = (
            self._reconstruction_instruments_panel.update_feature_data
        )
        self._reconstruction_instruments_logic.on_channel_changed = on_rewrite_requested

        self._reconstruction_instruments_panel.on_instrument_export = gated(
            after_edits, self._exports.export_instrument
        )
        self._reconstruction_instruments_panel.on_reconstruction_instrument_hovered = (
            self._reconstruction_plot_panel.set_overlay
        )
        self._reconstruction_instruments_panel.on_pitch_value_changed = (
            self._reconstruction_instruments_logic.handle_pitch_value_changed
        )
        self._reconstruction_instruments_panel.on_envelope_changed = (
            self._reconstruction_instruments_logic.handle_envelope_changed
        )
        self._reconstruction_instruments_panel.on_piano_key_pressed = self._reconstruction_keys.press_computer_key
        self._reconstruction_instruments_panel.on_piano_key_lifted = self._reconstruction_keys.lift_computer_key
        self._reconstruction_instruments_panel.on_audition_generator_changed = (
            self._instrument_audition_logic.set_generator
        )
        self._instrument_audition_logic.on_waveform_changed = self._reconstruction_plot_panel.update_instrument_view
        self._reconstruction_instruments_logic.on_display_refreshed = self._instrument_audition_logic.refresh

    def _update_reconstruction_view(
        self,
        view_model: ReconstructionViewModel,
    ) -> None:
        """Fans the reconstruction view model out to the audio and plot cards."""
        self._reconstruction_audio_panel.update_view(view_model)
        self._reconstruction_plot_panel.update_view(view_model)

    def create_tab(self) -> None:
        with dpg.tab(
            tag=TAG_GLOBAL_TAB_RECONSTRUCTION,
            parent=TAG_GLOBAL_TABS,
            label=self._language_manager["global.menu.label.tab_reconstruction"],
        ):
            self._side_panel_count = TabColumns.build(
                panel_gap=self._geometry.panel_gap,
                columns=[
                    side_column(self._geometry, tag=_LEFT_COLUMN_TAG, build=self._browser_panel.create_panel),
                    ColumnSpec(
                        tag=_CENTER_COLUMN_TAG,
                        build=self._build_reconstruction_column,
                        theme=TAG_GLOBAL_THEME_PANEL_GROUND,
                        border=False,
                    ),
                    ColumnSpec(
                        tag=_RIGHT_COLUMN_TAG,
                        build=self._reconstruction_instruments_panel.create_panel,
                        theme=TAG_GLOBAL_THEME_PANEL_GROUND,
                        width=self._instruments_width,
                        height=self._right_height,
                        no_scrollbar=True,
                        border=False,
                    ),
                ],
            )

        self._sync_browser_width()
        self._sync_instruments_width()

    def _build_reconstruction_column(self, parent: str) -> None:
        """Stacks the audio, plot, and stems cards down the center column."""
        self._reconstruction_audio_panel.create_panel(parent)
        dpg.add_spacer(height=self._geometry.panel_gap, parent=parent)
        self._reconstruction_plot_panel.create_panel(parent)
        dpg.add_spacer(height=self._geometry.panel_gap, parent=parent)
        self._reconstruction_stems_panel.create_panel(parent)

    def _play_from(self, position: int) -> None:
        """Sounds the audio from the sample a click on the waveform pointed at."""
        self._guarded_player.run_guarded(partial(self._reconstruction_player_logic.play_from, position))

    def _on_browser_recordings_requested(self, path: Path) -> None:
        """Hands the browser what a document names, where it has already been read."""
        recordings = self._browser_logic.recordings(path)
        if recordings is not None:
            self._browser_panel.update_recordings(path, recordings)

    def show_browser_recordings(self, path: Path, recordings: Tuple[NamedRecordingViewModel, ...]) -> None:
        """Hands the browser a reading that landed after the row asked for it."""
        self._browser_panel.update_recordings(path, recordings)

    def sync_responsive_layout(self) -> None:
        """Refits both side columns to the current viewport, the entry the resize handler calls."""
        self._sync_browser_width()
        self._sync_instruments_width()

    def _sync_browser_width(self) -> None:
        """Shrinks the browser column to the collapse rail when collapsed, else sizes it to the viewport width."""
        fit_side_column(
            self._geometry,
            _LEFT_COLUMN_TAG,
            collapsed=self._browser_panel.collapsed,
            base_width=self._geometry.side_width,
            side_panel_count=self._side_panel_count,
        )

    def _sync_instruments_width(self) -> None:
        """Shrinks the instruments column to the collapse rail when collapsed, else sizes it to the viewport width."""
        fit_side_column(
            self._geometry,
            _RIGHT_COLUMN_TAG,
            collapsed=self._reconstruction_instruments_panel.collapsed,
            base_width=self._instruments_width,
            side_panel_count=self._side_panel_count,
        )

    def lock(self) -> None:
        self._browser_panel.lock()

    def unlock(self) -> None:
        self._browser_panel.unlock()

    def refresh_browser(self) -> None:
        self._browser_panel.refresh()

    def save_browser_shape(self) -> None:
        """Writes down the rows the browser stands open, so a later run brings them back."""
        self._session_manager.set_expanded_rows(
            self._browser_panel.tag,
            self._browser_panel.expanded_rows,
        )

    def repaint_browser_favorites(
        self,
        nodes: Sequence[FileSystemNode],
    ) -> None:
        self._browser_panel.update_favorite_indicators(nodes)

    def display_reconstruction(self) -> None:
        self._instrument_editor.release_instrument()
        self._reconstruction_panel_logic.display_reconstruction()
        self._reconstruction_instruments_logic.update_display()

    def edit_instrument(self, voice_id: str) -> None:
        """Puts an instrument in front of the tab, closing whatever reconstruction it held.

        The tab describes one voice at a time — an instrument stands on no recording, so the waveform,
        the plot and the stems beside the instruments panel have nothing of it to draw.
        """
        self._instrument_editor.edit_instrument(voice_id)
        self._reconstruction_instruments_logic.update_display()

    def release_instrument(self) -> None:
        """Lets go of the instrument the tab held, which is what opening a reconstruction does."""
        self._instrument_editor.release_instrument()

    def follow_instrument(self, *, restored: bool) -> None:
        """Brings the instrument the tab holds in line with the project it belongs to.

        An instrument the project no longer holds leaves the tab empty. A restore hands a kept
        instrument the envelopes it had then, so the panel draws them. Any other change to the
        project leaves the panel as drawn, so a keystroke in the tracker keeps what the reader
        is writing here.
        """
        if not self._instrument_editor.holds_instrument:
            return

        if self._instrument_editor.instrument is None:
            self.close_instrument()
        elif restored:
            self._reconstruction_instruments_logic.update_display()

    def close_instrument(self) -> None:
        """Lets go of the instrument the tab holds and empties the tab, as a closed reconstruction leaves it.

        The waveform card draws the instrument's own audio while it is open, so it empties together
        with the instruments panel.
        """
        if not self._instrument_editor.holds_instrument:
            return

        self._instrument_editor.release_instrument()
        self.close_reconstruction()

    def close_reconstruction(self) -> None:
        self._reconstruction_panel_logic.close_reconstruction()
        self._reconstruction_instruments_logic.update_display()

    def _request_rate_change(self, nes_frequency: int) -> None:
        """Asks for the open document to be re-timed to the rate the reader typed."""
        self._on_rewrite_requested(RateChange(nes_frequency=nes_frequency))

    def _request_listening(self) -> None:
        """Asks for what the reader hears to be rendered, where the screen holds no audio for it yet."""
        self._on_rewrite_requested(ListeningChange())

    def update_reconstruction(self, *, refit_waveform: bool = False) -> None:
        """Re-answers every reading of an edited document whose envelopes the instruments panel already draws.

        A regenerated instrument carries the envelopes the panel's own edit wrote, and a retune
        carries every envelope over, so the panel keeps what it draws and a field the reader is
        typing in keeps its text.
        """
        self._reconstruction_panel_logic.update_reconstruction(refit_waveform=refit_waveform)
        self._reconstruction_instruments_logic.refresh_view()

    def redraw_reconstruction(self, *, refit_waveform: bool) -> None:
        """Re-answers every reading of a document rewritten outside the instruments panel, envelopes included.

        A removed recording releases the frames it held, and a replaced sample or an undo brings
        envelopes of its own, so the panel draws the document as it now stands and the next edit
        starts from it. A document timed at another NES frequency spans another length, so the
        caller that knows this asks the waveform to re-fit.
        """
        self._reconstruction_panel_logic.update_reconstruction(refit_waveform=refit_waveform)
        self._reconstruction_instruments_logic.update_display()

    def abandon_showing(self) -> None:
        """Lets the panel go of what it owes the reader, where the worker will never render it."""
        self._reconstruction_panel_logic.abandon_showing()

    def redraw_listening(self, *, envelopes_changed: bool) -> None:
        """Shows what the reader hears once the worker has rendered it, where a showing waited for it.

        A box on the stems card changes the part the instruments panel draws, so the panel is
        redrawn when the rendering brought envelopes for a new choice; a box above the waveform
        leaves them as they were.
        """
        self._reconstruction_panel_logic.redraw_listening()
        if envelopes_changed:
            self._reconstruction_instruments_logic.update_display()

    def show_work(self, work: Optional[Work]) -> None:
        self._reconstruction_plot_panel.show_work(work)

    def toggle_channel(self, channel: ChannelName) -> None:
        """Switches one channel's slice in and out of the waveform and of what plays."""
        self._reconstruction_plot_panel.toggle_channel(channel)

    @property
    def player(self) -> AudioPlayerProtocol:
        return self._guarded_player

    def request_export_wav_dialog(self) -> None:
        self._reconstruction_panel_logic.request_export_wav_dialog()

    def request_export_instruments_dialog(self, export_format: ExportFormat) -> None:
        """Writes the loaded reconstruction's slices in ``export_format``."""
        self._exports.request_instruments(export_format)

    def arm_keys(self) -> None:
        """Keeps what a key sounds in step with the voice in front of the tab, once a frame."""
        self._key_arming.arm()

    def _follow_key(self, position: Optional[int]) -> None:
        """Marks where the note a key struck stands on the plot card, taking the mark off once it ends."""
        self._reconstruction_plot_panel.set_playback_position(START_OF_AUDIO if position is None else position)

    def _on_audio_data_changed(self, audio_data: Optional[AudioData]) -> None:
        if audio_data is None:
            self._reconstruction_player_logic.clear_audio()
        else:
            self._reconstruction_player_logic.load_audio_data(audio_data)

    def set_on_add_to_sequencer(self, callback: PathCallback) -> None:
        self._browser_panel.on_add_to_sequencer = callback

    def set_can_add_to_sequencer(self, predicate: Callable[[], bool]) -> None:
        self._browser_panel.can_add_to_sequencer = predicate

    def locate_original_audio(self) -> None:
        """Reveals the loaded reconstruction's original audio file in the OS file manager."""
        self._reconstruction_panel_logic.handle_locate_original_audio()

    def open_reconstruction_in_explorer(self) -> None:
        """Reveals the loaded reconstruction's own file in the OS file manager."""
        self._reconstruction_panel_logic.open_reconstruction_in_explorer()

    def load_reconstruction(self, filepath: Path) -> None:
        self._browser_panel.lock()
        try:
            self._loading.load(filepath)
        finally:
            self._browser_panel.unlock()
