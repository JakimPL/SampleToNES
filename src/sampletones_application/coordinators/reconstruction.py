from functools import partial
from pathlib import Path
from typing import Callable, Optional, Tuple

from sampletones_application.categories.hierarchy import Tab
from sampletones_application.categories.manager import LanguageManager
from sampletones_application.config.managers.session import SessionManager
from sampletones_application.coordinators.tabs.reconstruction import (
    ReconstructionTabCoordinator,
)
from sampletones_application.logic.history.manager import HistoryManager
from sampletones_application.logic.project.controller import ProjectController
from sampletones_application.logic.reconstruction.edit import (
    ChannelEdit,
    ReconstructionEdit,
    Retune,
    StemRemoval,
)
from sampletones_application.logic.reconstruction.manager import ReconstructionManager
from sampletones_application.logic.reconstruction.rewrites.queue import (
    ReconstructionRewrites,
)
from sampletones_application.logic.reconstruction.rewrites.steps import (
    AfterEdits,
    Rewrite,
)
from sampletones_application.tags.general import (
    TAG_GLOBAL_DIALOG_EXIT_CONFIRMATION,
    TAG_GLOBAL_DIALOG_RECONSTRUCTION_REPLACED,
    TAG_GLOBAL_DIALOG_RECONSTRUCTION_SAVED,
)
from sampletones_application.utils.callbacks.gates import ignore
from sampletones_application.utils.file_dialogs.api import (
    open_file_dialog,
    save_file_dialog,
)
from sampletones_application.utils.file_dialogs.filter import FileFilter
from sampletones_application.utils.file_dialogs.result import ignore_none_path
from sampletones_application.utils.gui.dialogs import DialogsRenderer
from sampletones_application.utils.gui.dialogs.outcome import SaveOutcome
from sampletones_core.audio import AudioDeviceManager
from sampletones_core.project.voices.instrument import Instrument
from sampletones_core.project.voices.sample import Sample
from sampletones_core.reconstructions import Reconstruction
from sampletones_shared.exceptions import SampleToNESError
from sampletones_shared.logger import logger
from sampletones_shared.paths.extensions import EXT_FILE_RECONSTRUCTION
from sampletones_shared.types.callback import Callback, VoidCallback
from sampletones_shared.utils.system.paths import first_missing, get_filename


class ReconstructionCoordinator:
    """
    The application's single authority on reconstruction document lifecycle.

    A reconstruction is a cross-cutting concern:
    - It can be opened from multiple entry points.
    - It must be saved before replacement.
    - Its dirty/saved state drives the window title.
    - Every edit of the open document flows through it, one step at a time in the
      reader's order (see :class:`ReconstructionRewrites`), so all reconstruction
      mutations remain centralized.
    - Every change from outside the tab that replaces the open document passes
      through it: opening a project voice, a replaced sample, and a project change
      that restores, removes or lets go of the voice the tab shows. Each puts away
      the edits meant for the document it replaces.

    The reconstructions tab is wired in after construction through
    ``set_reconstructions_tab``; ``_tab`` asserts it is present before first use.
    """

    def __init__(
        self,
        reconstruction_manager: ReconstructionManager,
        session_manager: SessionManager,
        rewrites: ReconstructionRewrites,
        audio_device_manager: AudioDeviceManager,
        project_controller: ProjectController,
        history: HistoryManager,
        *,
        dialogs: DialogsRenderer,
        language_manager: LanguageManager,
        on_tab_switch: Callback,
        on_session_state_changed: VoidCallback,
        on_reconstruction_updated: Callable[[ReconstructionEdit], None],
    ) -> None:
        self._reconstruction_manager = reconstruction_manager
        self._session_manager = session_manager
        self._rewrites = rewrites
        self._audio_device_manager = audio_device_manager
        self._project_controller = project_controller
        self._history = history
        self._reconstructions_tab: Optional[ReconstructionTabCoordinator] = None
        self._dialogs = dialogs
        self._language_manager = language_manager
        self._on_tab_switch = on_tab_switch
        self._on_session_state_changed_callback = on_session_state_changed
        self._on_reconstruction_updated_callback = on_reconstruction_updated

        self._reconstruction_manager.session.on_state_changed = self._on_state_changed
        self._rewrites.on_edit = self.apply_edit
        self._rewrites.on_dropped = self._redraw_open_document
        self._rewrites.on_failed = self._report_rebuild_failure
        self._rewrites.on_busy_changed = self._set_reconstruction_dimmed
        self._reconstruction_manager.set_callbacks(
            on_reconstruction_loaded=self.on_reconstruction_loaded,
            on_reconstruction_closed=self._on_closed,
        )

    def set_reconstructions_tab(self, tab: ReconstructionTabCoordinator) -> None:
        self._reconstructions_tab = tab

    @property
    def _tab(self) -> ReconstructionTabCoordinator:
        if self._reconstructions_tab is None:
            raise RuntimeError("set_reconstructions_tab has not been called")

        return self._reconstructions_tab

    @property
    def reconstruction_name(self) -> Optional[str]:
        return self._reconstruction_manager.session.name

    def is_loaded(self) -> bool:
        return self._reconstruction_manager.session.is_loaded

    def is_unsaved(self) -> bool:
        return self._reconstruction_manager.session.unsaved_changes

    def is_saveable(self) -> bool:
        return self._reconstruction_manager.is_file_backed

    def _requires_save_confirmation(self) -> bool:
        """Reports pending edits that a save prompt can resolve.

        A prompt is warranted only for a standalone reconstruction with unsaved changes. A
        project sample has no file of its own, and its edits belong to the project — closing or
        replacing it loses nothing, so it needs no prompt.
        """
        return self.is_unsaved() and not self._reconstruction_manager.is_project_sample

    def check_loaded(self) -> bool:
        if not self.is_loaded():
            logger.warning("No reconstruction loaded; cannot proceed")
            self._dialogs.show_reconstruction_not_loaded()
            return False

        return True

    def save_as_dialog(self) -> SaveOutcome:
        """Saves the open reconstruction to a file the reader picks, and says so once it is written."""
        outcome = self._save_to_chosen_file()
        if outcome is SaveOutcome.WRITTEN:
            self._dialogs.show_info(
                TAG_GLOBAL_DIALOG_RECONSTRUCTION_SAVED,
                self._language_manager["global.dialog.message.reconstruction_saved_successfully"],
                self._language_manager["global.dialog.title.reconstruction_saved"],
            )

        return outcome

    def _save_to_chosen_file(self) -> SaveOutcome:
        """Asks where the open reconstruction goes, writes it there and adopts that file as its own.

        A document that came from a file offers that file's place, and one without a file offers
        the reconstructions folder under its own name.
        """
        reconstruction_data = self._reconstruction_manager.current_reconstruction
        if reconstruction_data is None:
            return SaveOutcome.CALLED_OFF

        filepath = reconstruction_data.filepath
        if filepath is not None:
            default_filename = filepath.name
            default_path = str(filepath.parent)
        else:
            default_filename = get_filename(reconstruction_data.name, EXT_FILE_RECONSTRUCTION)
            default_path = str(self._session_manager.get_reconstruction_path())

        chosen = save_file_dialog(
            title=self._language_manager["global.dialog.title.save_reconstruction"],
            initial_directory=default_path,
            default_filename=default_filename,
            filters=self._reconstruction_filters(),
        )
        if chosen is None:
            return SaveOutcome.CALLED_OFF

        try:
            self._reconstruction_manager.save_reconstruction_as(chosen)
        except (OSError, SampleToNESError) as exception:
            self._report_save_failure(exception, chosen)
            return SaveOutcome.FAILED

        self._session_manager.set_reconstruction_path(chosen.parent)
        self._session_manager.set_current_reconstruction(chosen)
        self._tab.display_reconstruction()
        return SaveOutcome.WRITTEN

    def _reconstruction_filters(self) -> Tuple[FileFilter, ...]:
        """The single type a reconstruction is written as and read from."""
        return (
            FileFilter.for_extensions(
                self._language_manager["global.dialog.filter.reconstruction"],
                [EXT_FILE_RECONSTRUCTION],
            ),
        )

    def _load_dialog(self) -> None:
        filepath = open_file_dialog(
            title=self._language_manager["reconstructions.browser.title.load_reconstruction_dialog"],
            initial_directory=self._session_manager.get_reconstruction_path(),
            filters=self._reconstruction_filters(),
        )

        self._handle_load(filepath)

    @ignore_none_path
    def load(self, filepath: Path) -> None:
        return self._tab.load_reconstruction(filepath)

    def open(self, filepath: Optional[Path] = None) -> None:
        """Loads ``filepath``, or the reconstruction file the reader picks where none is named."""
        if filepath is None:
            self._load_dialog()
        else:
            self.load(filepath)

    def guard_load(self, proceed: VoidCallback, decline: VoidCallback) -> None:
        """Lets another document take the open one's place, offering first to save unsaved changes.

        The signature is a :data:`Gate`, so the question leads the loading's conversation.
        """
        self._save_first(
            title=self._language_manager["global.dialog.title.load_unsaved_reconstruction"],
            message=self._language_manager["global.dialog.message.load_unsaved_reconstruction"],
            ok_label=self._language_manager["global.dialog.label.discard"],
            proceed=proceed,
            decline=decline,
        )

    def load_with_confirmation(self, filepath: Optional[Path] = None) -> None:
        """Loads ``filepath``, or the file the reader picks, once unsaved changes are answered for."""
        self.guard_load(partial(self.open, filepath), ignore)

    def load_converted(self, filepath: Path) -> None:
        """Loads the reconstruction a conversion wrote, asking first about unsaved changes.

        A conversion can write over the very file the open document came from, and a save would
        then write the old document over the new one. The question in that case is whether to
        discard the changes and load, and Cancel keeps them for a save to another file. Every other
        document is loaded the way one opened by hand is.
        """
        if self._requires_save_confirmation() and self._reconstruction_manager.is_backed_by(filepath):
            self._dialogs.show_confirmation(
                tag=TAG_GLOBAL_DIALOG_RECONSTRUCTION_REPLACED,
                message=self._language_manager["global.dialog.message.load_replaced_reconstruction"],
                title=self._language_manager["global.dialog.title.load_unsaved_reconstruction"],
                on_confirm=lambda: self.load(filepath),
                ok_label=self._language_manager["global.dialog.label.discard"],
            )
            return

        self.load_with_confirmation(filepath)

    def load_reconstruction_safely(self, path: Path) -> None:
        """Loads the persisted reconstruction when the application starts.

        Startup restore happens automatically, so a failed load is recovered silently:
        the stale session pointer is cleared so a missing, moved, or corrupt file leaves
        the next launch starting from a clean slate. Only known domain and I/O failures
        are absorbed; unexpected errors propagate.
        """
        try:
            self._reconstruction_manager.load_reconstruction(path)
        except (SampleToNESError, OSError) as exception:
            logger.warning(f"Could not restore reconstruction from {logger.format_path(path)}: {exception}")
            self._session_manager.set_current_reconstruction(None)

    def guard_exit(self, proceed: VoidCallback, decline: VoidCallback) -> None:
        """Lets the exit go on, asking first to save a standalone reconstruction with unsaved changes.

        A project sample's changes belong to the project, which the exit asks about on its own.
        Cancel keeps the application open and turns the exit away.
        """
        self._save_first(
            title=self._language_manager["global.dialog.title.exit_confirmation"],
            message=self._language_manager["global.dialog.message.exit_unsaved_reconstruction"],
            ok_label=self._language_manager["global.dialog.label.exit"],
            proceed=proceed,
            decline=decline,
        )

    @ignore_none_path
    def _handle_load(self, filepath: Path) -> None:
        self._session_manager.set_reconstruction_path(filepath.parent)
        self._tab.load_reconstruction(filepath)

    def save(self, filepath: Optional[Path] = None) -> SaveOutcome:
        """Saves the open reconstruction, reporting what the save came to.

        The save prompts wait on this: a document written to disk lets them go on, a save the
        reader calls off asks again, and a write that fails shows its error. A standalone document
        whose file was taken away asks where to go, the way Save As does, so its save prompt has a
        way forward.
        """
        manager = self._reconstruction_manager
        if filepath is None and not manager.is_file_backed and not manager.is_project_sample:
            return self._save_to_chosen_file()

        try:
            written = self._reconstruction_manager.save_reconstruction(filepath)
        except (OSError, SampleToNESError) as exception:
            self._report_save_failure(exception, filepath or self._reconstruction_manager.filepath)
            return SaveOutcome.FAILED

        return SaveOutcome.WRITTEN if written else SaveOutcome.CALLED_OFF

    def _report_save_failure(self, exception: Exception, filepath: Optional[Path]) -> None:
        logger.error_with_traceback(
            exception,
            f"Failed to save reconstruction to {filepath}",
        )
        self._dialogs.show_error(
            exception,
            self._language_manager["global.dialog.message.reconstruction_save_failed"],
        )

    def guard_close(self, proceed: VoidCallback, decline: VoidCallback) -> None:
        """Lets the open document close, offering first to save unsaved changes.

        The signature is a :data:`Gate`, so the question leads the closing's conversation.
        """
        self._save_first(
            title=self._language_manager["global.dialog.title.close_unsaved_reconstruction"],
            message=self._language_manager["global.dialog.message.close_unsaved_reconstruction"],
            ok_label=self._language_manager["global.dialog.label.close"],
            proceed=proceed,
            decline=decline,
        )

    def close(self) -> None:
        """Puts the open document away, with the edits still on their way to it."""
        self._drop_pending()
        self._reconstruction_manager.close_reconstruction()

    def request_rewrite(self, rewrite: Rewrite) -> None:
        """Asks for a change of the open document, which it takes after the changes asked for before it."""
        self._rewrites.request(rewrite)

    def after_edits(self, gesture: VoidCallback) -> None:
        """Runs a gesture that reads or puts away the whole document once the edits before it have landed.

        Undo, a save, a load or an export acts on the document the reader has drawn, so it waits
        for the edits still on their way. With nothing on its way, the gesture runs at once. The
        signature is a :data:`Wait`, so the wait can lead a chain of gates.
        """
        self._rewrites.request(AfterEdits(gesture))

    def _drop_pending(self) -> None:
        """Puts away the edits meant for the open document, which an outside change is about to replace."""
        self._rewrites.drop()

    def on_reconstruction_loaded(self) -> None:
        reconstruction_data = self._reconstruction_manager.current_reconstruction
        if reconstruction_data is None:
            raise RuntimeError("No reconstruction is loaded after loading process")

        self._drop_pending()
        self._audio_device_manager.stop()
        missing_path = first_missing(reconstruction_data.reconstruction.audio_filepath)
        if missing_path is not None:
            self._dialogs.show_file_not_found(
                missing_path,
                self._language_manager["reconstructions.browser.message.audio_file_not_found"],
            )

        filepath = reconstruction_data.filepath
        self._tab.display_reconstruction()
        self._session_manager.set_current_reconstruction(filepath)
        self._on_tab_switch(Tab.RECONSTRUCTIONS)

    def _on_closed(self) -> None:
        self._tab.close_reconstruction()
        self._session_manager.set_current_reconstruction(None)

    def apply_edit(self, edit: ReconstructionEdit) -> None:
        """Applies an edited reconstruction across the open document and project.

        Every edit of the open document lands here as the rewrites take it, so one path answers a
        regenerated instrument, a removed recording and a retune alike, in the reader's order. The
        owning-sample hook runs first and records the edit against the project history as the
        ``edit`` describes itself, so the history holds it by the time the tab shows it. The open
        document then rebinds to the new reconstruction, the same object the sample now holds, and
        the tab shows it.
        """
        self._on_reconstruction_updated_callback(edit)
        self._reconstruction_manager.apply_edited(edit.reconstruction)
        self._show_edit(edit)
        self._reconstruction_manager.mark_updated()

    def _show_edit(self, edit: ReconstructionEdit) -> None:
        """Shows the edited document, redrawing the instruments panel where the edit came from elsewhere.

        A regenerated instrument carries the envelopes the panel's own edit wrote, so the panel
        keeps drawing them and a field the reader is typing in keeps its text. A retune carries
        every envelope over too, and its audio spans another length, so the waveform re-fits. A
        removed recording releases frames the panel drew as sounding, so the panel draws every
        channel as the document now holds it.
        """
        match edit:
            case ChannelEdit():
                self._tab.update_reconstruction()
            case Retune():
                self._tab.update_reconstruction(refit_waveform=True)
            case StemRemoval():
                self._tab.redraw_reconstruction(refit_waveform=False)

    def open_project_voice(self, voice_id: str) -> None:
        """Opens a voice of the project on the Reconstructions tab, in the terms of its kind.

        Either kind takes the place of the open document, so a standalone document with unsaved
        changes is offered a save first, the way loading a file offers it.
        """
        self._save_first(
            title=self._language_manager["global.dialog.title.edit_voice_unsaved_reconstruction"],
            message=self._language_manager["global.dialog.message.edit_voice_unsaved_reconstruction"],
            ok_label=self._language_manager["global.dialog.label.discard"],
            proceed=lambda: self._open_project_voice(voice_id),
            decline=ignore,
        )

    def _open_project_voice(self, voice_id: str) -> None:
        """Puts a voice of the project in front of the tab.

        A sample opens as the reconstruction behind it, waveform and stems and all, and the
        document remembers the voice it is. An instrument stands on no recording, so the tab
        shows its envelopes alone. Either kind brings that tab to the front, so the voice a
        reader asked to edit is the one in view.
        """
        match self._project_controller.project.voice(voice_id):
            case Sample() as sample:
                self._tab.release_instrument()
                self._reconstruction_manager.load_reconstruction_object(
                    sample.reconstruction,
                    name=sample.name,
                    voice_id=sample.id,
                )
            case Instrument():
                self._drop_pending()
                self._tab.edit_instrument(voice_id)
                self._on_tab_switch(Tab.RECONSTRUCTIONS)
            case _:
                logger.warning(f"Cannot edit unknown project voice: {voice_id}")

    def replace_sample(self, voice_id: str, reconstruction: Reconstruction) -> None:
        """Shows the reconstruction a sample now holds, where the tab has that sample open.

        A sample whose audio is substituted keeps its id, so the open document takes the incoming
        reconstruction along. It brings envelopes of its own, so the tab redraws the instruments
        panel from it.

        Args:
            voice_id: The sample that received a new reconstruction.
            reconstruction: The reconstruction the sample now holds.
        """
        if self._reconstruction_manager.voice_id == voice_id:
            self._rebind(reconstruction)

    def follow_project(self) -> None:
        """Closes the voice the tab shows once the project stops holding it.

        Every change to the project reaches here, the tab's own edits included. An edit writes
        the project before the open document shows it, so a voice the project still holds is
        left as it stands and the panel keeps what the reader is drawing.
        """
        self._follow(restored=False)

    def follow_replaced_project(self) -> None:
        """Follows the voice the tab shows into a project put in place of the one it belonged to.

        An undo, a redo or a history jump installs a snapshot that keeps every voice's id, so a
        voice it keeps is shown as restored and one it took out closes. Any other replacement
        (a new, opened or closed project) lets the voice go, since a reopened file brings back
        the same ids.
        """
        if self._history.is_restoring:
            self._follow(restored=True)
        else:
            self._let_go_of_project_voice()

    def _follow(self, *, restored: bool) -> None:
        """Brings the voice in front of the tab in line with the project.

        A sample the project no longer holds closes. A restore hands a kept sample the
        reconstruction it held then, which the tab rebinds to. The instrument the tab holds
        follows by the same rule.
        """
        voice_id = self._reconstruction_manager.voice_id
        if voice_id is not None:
            match self._project_controller.project.voice(voice_id):
                case Sample() as sample:
                    if restored:
                        self._rebind(sample.reconstruction)
                case _:
                    self.close()

        self._tab.follow_instrument(restored=restored)

    def _let_go_of_project_voice(self) -> None:
        """Closes a project voice the tab shows, leaving a standalone document open."""
        if self._reconstruction_manager.is_project_sample:
            self.close()

        self._tab.close_instrument()

    def _rebind(self, reconstruction: Reconstruction) -> None:
        """Points the open document at the reconstruction its sample now holds, and redraws it.

        A reconstruction timed at another NES frequency spans another length, so the waveform
        re-fits to it. The document the sample already holds needs no redraw.
        """
        open_reconstruction = self._reconstruction_manager.reconstruction
        if open_reconstruction is None or reconstruction is open_reconstruction:
            return

        retimed = reconstruction.config.nes_frequency != open_reconstruction.config.nes_frequency
        self._drop_pending()
        self._reconstruction_manager.apply_edited(reconstruction)
        self._tab.redraw_reconstruction(refit_waveform=retimed)

    def _redraw_open_document(self) -> None:
        """Draws the open document as it stands, where the panel drew a change that will never land."""
        if self.is_loaded():
            self._tab.redraw_reconstruction(refit_waveform=False)

    def _report_rebuild_failure(self, exception: Exception) -> None:
        logger.error_with_traceback(exception, "Regeneration failed")
        self._dialogs.show_error(exception)

    def _set_reconstruction_dimmed(self, dimmed: bool) -> None:
        """Fades the reconstruction waveform while the open document is being rewritten.

        The dim follows the rewrites' busy span, so a continuous edit stream keeps the waveform
        faded until the last step lands, and it restores once nothing runs or waits.
        """
        if self._reconstructions_tab is None:
            return

        self._reconstructions_tab.set_reconstruction_dimmed(dimmed)

    def _on_state_changed(self) -> None:
        self._on_session_state_changed_callback()

    def _save_first(
        self,
        *,
        title: str,
        message: str,
        ok_label: str,
        proceed: VoidCallback,
        decline: VoidCallback,
    ) -> None:
        """Goes on with ``proceed``, offering first to save a standalone document with unsaved changes.

        Args:
            title: The prompt's title.
            message: What the prompt says would be lost.
            ok_label: The label of the answer that goes on without saving.
            proceed: What runs once the document is saved, or once the reader lets the changes go.
            decline: What runs once the reader keeps the changes, or once the save fails.
        """
        if not self._requires_save_confirmation():
            proceed()
            return

        self._dialogs.show_save_confirmation(
            tag=TAG_GLOBAL_DIALOG_EXIT_CONFIRMATION,
            title=title,
            message=message,
            on_save=self.save,
            on_confirm=proceed,
            on_cancel=decline,
            ok_label=ok_label,
        )
