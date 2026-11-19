from pathlib import Path
from typing import Dict, Mapping, Optional

from sampletones_application.categories.export import ExportMessages
from sampletones_application.categories.manager import LanguageManager
from sampletones_application.categories.truncation import TruncationMessages
from sampletones_application.coordinators.export.instrument import InstrumentExportCoordinator
from sampletones_application.coordinators.export.setup import ExportSetup
from sampletones_application.coordinators.filters import instrument_filter
from sampletones_application.logic.reconstruction.editor import InstrumentEditor
from sampletones_application.logic.reconstruction.reconstruction import ReconstructionPanelLogic
from sampletones_application.services.export.error import ExportError
from sampletones_application.services.export.kind import ExportKind
from sampletones_application.services.export.result import ExportResult
from sampletones_application.services.export.success import ExportSuccess
from sampletones_application.utils.file_dialogs.api import save_file_dialog
from sampletones_application.utils.file_dialogs.filter import FileFilter
from sampletones_application.utils.file_dialogs.result import ignore_none_path
from sampletones_application.utils.gui.dialogs import DialogsRenderer
from sampletones_core.constants.enums import ChannelName
from sampletones_core.exporters.truncation import EnvelopeTruncation
from sampletones_core.exports.backend import ExportBackend
from sampletones_core.exports.format import ExportFormat
from sampletones_core.exports.scope import ExportScope
from sampletones_shared.paths.extensions import EXT_FILE_WAVE


class ReconstructionExports:
    """The files the tab writes: the open document's audio, its instruments, and the instrument in front of it.

    Each finished export is reported in the words of the file it wrote.
    """

    def __init__(
        self,
        panel_logic: ReconstructionPanelLogic,
        instrument_editor: InstrumentEditor,
        instrument_exports: InstrumentExportCoordinator,
        export_backends: Dict[ExportFormat, ExportBackend],
        format_setups: Mapping[ExportFormat, ExportSetup],
        *,
        dialogs: DialogsRenderer,
        language_manager: LanguageManager,
    ) -> None:
        self._panel_logic = panel_logic
        self._instrument_editor = instrument_editor
        self._instrument_exports = instrument_exports
        self._export_backends = export_backends
        self._format_setups = format_setups
        self._dialogs = dialogs
        self._language_manager = language_manager
        self._messages = ExportMessages.build(language_manager)

    def report(self, result: ExportResult) -> None:
        """Reports a finished export in the words of the artifact it produced."""
        messages = self._messages
        match result:
            case ExportSuccess(kind=ExportKind.WAV, filepath=filepath):
                self._dialogs.show_message_with_path(messages.wav_title, messages.wav_success, filepath)
            case ExportSuccess(kind=ExportKind.INSTRUMENT, filepath=filepath, truncation=truncation):
                self._dialogs.show_message_with_path(
                    messages.status_title,
                    _with_notice(messages.instrument_success, messages.instrument_truncated, truncation),
                    filepath,
                )
            case ExportSuccess(kind=ExportKind.SAMPLE, filepath=filepath, truncation=truncation):
                self._dialogs.show_message_with_path(
                    messages.status_title,
                    _with_notice(messages.instruments_success, messages.instruments_truncated, truncation),
                    filepath,
                )
            case ExportError(kind=ExportKind.WAV, exception=exception):
                self._dialogs.show_error(exception, messages.wav_failed)
            case ExportError(kind=ExportKind.INSTRUMENT, exception=exception):
                self._dialogs.show_error(exception, messages.instrument_failed)
            case ExportError(kind=ExportKind.SAMPLE, exception=exception):
                self._dialogs.show_error(exception, messages.instruments_failed)

    def report_dropped(self, filepath: Path) -> None:
        """Reports an export that waited for a sound the worker never rendered, in the WAV dialog's words."""
        self._dialogs.show_message_with_path(self._messages.wav_title, self._messages.wav_dropped, filepath)

    def export_instrument(self, channel_name: ChannelName) -> None:
        """Writes the instrument the tab's ``channel_name`` tab holds, wherever it is asked for.

        An instrument reaches a file the same way whichever surface asked for it, so the whole
        gesture from here on belongs to the shared exporter; what the tab contributes is which
        instrument it has in front of it. A voice written by hand is one the pool holds, so it is
        written by voice and the sequencer's voice menu writes the same file for it.
        """
        instrument = self._instrument_editor.instrument
        if instrument is not None:
            self._instrument_exports.request_voice(instrument.id, None)
            return

        exportable = self._panel_logic.exportable_instrument(channel_name)
        if exportable is not None:
            self._instrument_exports.request(exportable.source, exportable.name)

    def request_instruments(self, export_format: ExportFormat) -> None:
        """Writes the loaded reconstruction's slices in ``export_format``, asking first for what the
        format leaves open: its own setup where it has one, and the destination alone otherwise."""
        if export_format in self._format_setups:
            request = self._panel_logic.sample_request()
            if request is not None:
                self._format_setups[export_format].open_sample(export_format, request)

            return

        self._panel_logic.request_export_instruments_dialog(export_format)

    def open_instruments_dialog(self, default_filename: str, default_path: str, export_format: ExportFormat) -> None:
        """Prompts for the destination the loaded reconstruction's slices are named after.

        The format was chosen with the action, so the dialog offers its file type alone: a
        format that gathers the whole reconstruction into one document writes it at the
        destination, while one that keeps an instrument per file writes its slices beside it.
        """
        destination = save_file_dialog(
            title=self._language_manager["reconstructions.instruments.title.export_instruments_dialog"],
            initial_directory=default_path,
            default_filename=default_filename,
            filters=(
                instrument_filter(
                    self._language_manager,
                    export_format,
                    self._export_backends[export_format].extension(ExportScope.SAMPLE),
                ),
            ),
        )
        self._write_instruments(destination, export_format)

    def open_wav_dialog(self, default_filename: str, default_path: str) -> None:
        filepath = save_file_dialog(
            title=self._messages.wav_title,
            initial_directory=default_path,
            default_filename=default_filename,
            filters=(FileFilter.for_extensions(self._language_manager["global.dialog.filter.wave"], [EXT_FILE_WAVE]),),
        )
        self._write_wav(filepath)

    @ignore_none_path
    def _write_instruments(self, destination: Path, export_format: ExportFormat) -> None:
        self._panel_logic.handle_export_instruments_confirmed(destination, export_format)

    @ignore_none_path
    def _write_wav(self, filepath: Path) -> None:
        self._panel_logic.handle_export_wav_confirmed(filepath)


def _with_notice(success: str, shortened: TruncationMessages, truncation: Optional[EnvelopeTruncation]) -> str:
    """Follows the success line with the frames the format's value limit left out."""
    notice = shortened.notice(truncation)
    if notice is None:
        return success

    return f"{success}\n\n{notice}"
