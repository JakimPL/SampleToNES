from pathlib import Path
from typing import Callable, Optional

from sampletones_application.categories.instrument import InstrumentImportMessages
from sampletones_application.categories.manager import LanguageManager
from sampletones_application.config.managers.session import SessionManager
from sampletones_application.coordinators.tabs.sequencer.project import OpenProjectRequirement
from sampletones_application.logic.history.action import HistoryAction
from sampletones_application.logic.history.manager import HistoryManager
from sampletones_application.logic.project.controller import ProjectController
from sampletones_application.logic.sequencer.history_detail import SequencerHistoryDetail
from sampletones_application.logic.sequencer.voices import SequencerVoicesLogic
from sampletones_application.tags.general import TAG_GLOBAL_DIALOG_INSTRUMENT_IMPORTED
from sampletones_application.tags.sequencer import TAG_SEQUENCER_VOICES_DIALOG_REMOVE
from sampletones_application.utils.file_dialogs.api import open_file_dialog
from sampletones_application.utils.file_dialogs.filter import FileFilter
from sampletones_application.utils.file_dialogs.result import ignore_none_path
from sampletones_application.utils.gui.dialogs import DialogsRenderer
from sampletones_core.constants.enums import ChannelName
from sampletones_core.formats.famitracker.voice import ImportedVoice
from sampletones_core.utils.display import display_id
from sampletones_shared.exceptions import LoadInstrumentError
from sampletones_shared.logger import logger
from sampletones_shared.paths.extensions import EXT_FILE_INSTRUMENT, EXT_FILE_RECONSTRUCTION


class SequencerVoices:
    """The gestures that change what the pool holds: adding, importing, removing, renaming.

    Every one of them is a whole gesture, so each records the single history entry that takes the
    pool back to where it stood. A gesture reaching a file reads it before the pool is touched,
    which leaves a file the reader cannot use with the project and the history as they were.
    """

    def __init__(
        self,
        voices_logic: SequencerVoicesLogic,
        history: HistoryManager,
        history_detail: SequencerHistoryDetail,
        project_controller: ProjectController,
        session_manager: SessionManager,
        open_project: OpenProjectRequirement,
        *,
        dialogs: DialogsRenderer,
        language_manager: LanguageManager,
        import_messages: InstrumentImportMessages,
        import_reconstruction: Callable[[Path], None],
    ) -> None:
        self._voices_logic = voices_logic
        self._history = history
        self._history_detail = history_detail
        self._project_controller = project_controller
        self._session_manager = session_manager
        self._open_project = open_project
        self._dialogs = dialogs
        self._language_manager = language_manager
        self._import_messages = import_messages
        self._import_reconstruction = import_reconstruction

    def add_instrument(self) -> None:
        """Appends a hand-written voice, named for the position it takes in the list.

        An instrument arrives sustaining at full volume, so it plays as soon as it is placed and the
        envelopes stay the reader's to write; naming it by its position gives the list a readable
        entry until they rename it.
        """
        name = self._language_manager["sequencer.voices.template.instrument_name"].format(
            position=display_id(self._project_controller.voice_count),
        )
        with self._history.transaction(
            HistoryAction.ADD_INSTRUMENT,
            detail=self._history_detail.add_instrument(name),
        ):
            self._voices_logic.add_new_instrument(name)

    def add_instrument_from_channel(
        self,
        voice_id: str,
        channel_name: ChannelName,
    ) -> None:
        """Takes what one channel of a voice plays as an instrument of its own, then opens it.

        A recording states its channels as frames, and this reads one of them back as envelopes,
        so what the conversion found becomes a voice the reader edits by hand. The new voice is
        brought up where it is edited, since seeing those envelopes is what taking the channel out
        was for.

        Args:
            voice_id: The voice the channel belongs to.
            channel_name: The channel whose envelopes the instrument takes.
        """
        instrument = self._voices_logic.instrument_from_channel(voice_id, channel_name)
        if instrument is None:
            return

        with self._history.transaction(
            HistoryAction.ADD_INSTRUMENT,
            detail=self._history_detail.add_instrument(instrument.name),
        ):
            self._voices_logic.add_instrument(instrument)

        self._voices_logic.request_edit(instrument.id)

    def add_sample_from_file(self) -> None:
        """Brings a reconstruction saved anywhere on disk into the pool as a sample.

        The tree beside the list reaches the reconstructions folder, so a file kept elsewhere
        arrives through the system's own browser, which opens on the folder the last one came
        from.
        """
        filepath = open_file_dialog(
            title=self._language_manager["sequencer.voices.title.add_sample_dialog"],
            initial_directory=self._session_manager.get_reconstruction_path(),
            filters=(
                FileFilter.for_extensions(
                    self._language_manager["global.dialog.filter.reconstruction"],
                    [EXT_FILE_RECONSTRUCTION],
                ),
            ),
        )

        self._import_located_reconstruction(filepath)

    @ignore_none_path
    def _import_located_reconstruction(self, filepath: Path) -> None:
        self._session_manager.set_reconstruction_path(filepath.parent)
        self._import_reconstruction(filepath)

    def import_instrument(self) -> None:
        """Brings a FamiTracker instrument file into the pool as an instrument voice.

        The file arrives through the system's own browser, which opens on the folder the last
        instrument was written to or read from, so an export and the import that follows it meet
        in one place. A project is asked for first, since a voice needs a pool to land in.
        """
        if not self._open_project.met():
            return

        filepath = open_file_dialog(
            title=self._language_manager["sequencer.voices.title.import_instrument_dialog"],
            initial_directory=self._session_manager.get_instrument_path(),
            filters=(
                FileFilter.for_extensions(
                    self._language_manager["global.dialog.filter.famitracker_instrument"],
                    [EXT_FILE_INSTRUMENT],
                ),
            ),
        )

        self._import_located_instrument(filepath)

    @ignore_none_path
    def _import_located_instrument(self, filepath: Path) -> None:
        """Reads a located instrument file into the pool, then reports what it held.

        The file is read before the pool is touched, so a file the reader cannot use leaves the
        project as it stands and the history without an entry.
        """
        self._session_manager.set_instrument_path(filepath.parent)
        imported = self._read_instrument(filepath)
        if imported is None:
            return

        with self._history.transaction(
            HistoryAction.ADD_INSTRUMENT,
            detail=self._history_detail.add_instrument(imported.voice.name),
        ):
            self._voices_logic.add_instrument(imported.voice)

        self._report_import(imported)

    def remove(self, voice_id: str) -> None:
        """Removes a voice, confirming first only when a pattern still references it.

        An unused voice is dropped silently; a referenced one would clear every row
        that points at it, so the user confirms that loss first.
        """
        if not self._voices_logic.is_voice_used(voice_id):
            self._perform_remove(voice_id)
            return

        name = self._voices_logic.voice_name(voice_id)
        self._dialogs.show_confirmation(
            tag=TAG_SEQUENCER_VOICES_DIALOG_REMOVE,
            title=self._language_manager["global.dialog.title.remove_voice"],
            message=self._language_manager["global.dialog.message.remove_voice"].format(name=name),
            on_confirm=lambda: self._perform_remove(voice_id),
            ok_label=self._language_manager["global.dialog.label.remove"],
        )

    def submit_rename(self, voice_id: str, name: str) -> None:
        """Applies an inline rename, ignoring a blank name so the voice keeps its current one."""
        stripped = name.strip()
        if stripped:
            detail = self._history_detail.rename_voice(voice_id, stripped)
            with self._history.transaction(
                HistoryAction.RENAME_VOICE,
                detail=detail,
            ):
                self._voices_logic.rename_voice(voice_id, stripped)

    def _perform_remove(self, voice_id: str) -> None:
        detail = self._history_detail.remove_voice(voice_id)
        with self._history.transaction(
            HistoryAction.REMOVE_VOICE,
            detail=detail,
        ):
            self._voices_logic.remove_voice(voice_id)

    def _read_instrument(self, filepath: Path) -> Optional[ImportedVoice]:
        """Reads an instrument file, reporting a file the reader cannot take as a voice.

        Returns:
            Optional[ImportedVoice]: The voice the file describes, or ``None`` once the failure
            has been shown.
        """
        try:
            return self._voices_logic.read_instrument(filepath)
        except FileNotFoundError as exception:
            logger.error_with_traceback(exception, f"No instrument file at {filepath}")
            self._dialogs.show_file_not_found(
                filepath,
                self._language_manager["sequencer.voices.message.instrument_not_found"],
            )
        except (LoadInstrumentError, OSError) as exception:
            logger.error_with_traceback(exception, f"Failed to read an instrument from {filepath}")
            self._dialogs.show_error(exception)

        return None

    def _report_import(self, imported: ImportedVoice) -> None:
        """Names what the instrument file carried beyond the voice the pool took from it."""
        notice = self._import_messages.notice(imported.voice.name, imported.omissions)
        if notice is not None:
            self._dialogs.show_info(
                TAG_GLOBAL_DIALOG_INSTRUMENT_IMPORTED,
                notice,
                self._import_messages.title,
            )
