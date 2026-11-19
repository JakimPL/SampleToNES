from pathlib import Path
from typing import Optional, Tuple

from sampletones_application.categories.conversion import SkippedRecordingMessages
from sampletones_application.categories.manager import LanguageManager
from sampletones_application.categories.skipped import PARAGRAPH_BREAK
from sampletones_application.logic.main.converter.logic import ConverterLogic
from sampletones_application.logic.main.converter.run import ConversionSuccess
from sampletones_application.tags.main import (
    TAG_MAIN_CONVERTER_DIALOG_CANCEL,
    TAG_MAIN_CONVERTER_DIALOG_LOAD,
    TAG_MAIN_CONVERTER_DIALOG_OVERWRITE_TARGET,
)
from sampletones_application.utils.gui.dialogs import DialogsRenderer
from sampletones_shared.types.callback import VoidCallback


class ConversionPrompts:
    """What a conversion puts to the reader: what it needs before it starts, what it would write over,
    whether to stop it, and what it wrote.
    """

    def __init__(
        self,
        converter_logic: ConverterLogic,
        *,
        notice_tag: str,
        dialogs: DialogsRenderer,
        language_manager: LanguageManager,
        on_written: VoidCallback,
    ) -> None:
        self._converter_logic = converter_logic
        self._notice_tag = notice_tag
        self._dialogs = dialogs
        self._language_manager = language_manager
        self._on_written = on_written
        self._ttl_progress = language_manager["main.converter.title.progress_dialog"]
        self._skipped_recording_messages = SkippedRecordingMessages.build(language_manager)

    def report_error(self, error: Exception) -> None:
        self._dialogs.show_error(error, self._language_manager["main.converter.message.status_error"])

    def report_no_files(self) -> None:
        self._show_notice(self._language_manager["main.converter.message.status_no_files"])

    def report_no_channels(self) -> None:
        self._show_notice(self._language_manager["main.converter.message.status_no_channels"])

    def _show_notice(self, message: str) -> None:
        self._dialogs.show_info(self._notice_tag, message, self._ttl_progress)

    def confirm_overwriting(self, targets: Tuple[Path, ...]) -> None:
        """Asks before a conversion writes over the reconstructions already standing at its targets.

        Confirming writes over every one of them, so the prompt speaks for all of them: one is
        named by the path it stands at, and several are counted.
        """
        one = len(targets) == 1
        message = (
            self._language_manager["main.converter.message.overwrite_target_prompt"]
            if one
            else self._language_manager["main.converter.message.overwrite_targets_prompt"]
        )
        title = (
            self._language_manager["main.converter.title.overwrite_target_dialog"]
            if one
            else self._language_manager["main.converter.title.overwrite_targets_dialog"]
        )
        self._dialogs.show_confirmation(
            TAG_MAIN_CONVERTER_DIALOG_OVERWRITE_TARGET,
            message if one else message.format(count=len(targets)),
            title,
            lambda: self._converter_logic.start_conversion(confirmed=True),
            ok_label=self._language_manager["main.converter.label.overwrite_target_button"],
            path=targets[0] if one else None,
        )

    def confirm_cancel(self) -> None:
        """Asks before a running conversion stops, which drops the recordings still on their way."""
        self._dialogs.show_confirmation(
            TAG_MAIN_CONVERTER_DIALOG_CANCEL,
            self._language_manager["main.converter.message.cancel_prompt"],
            self._language_manager["main.converter.title.cancel_dialog"],
            self._converter_logic.cancel,
            ok_label=self._language_manager["main.converter.label.stop_button"],
            cancel_label=self._language_manager["main.converter.label.continue_button"],
        )

    def offer_written(self, success: ConversionSuccess) -> None:
        """Offers what the run wrote, with the recordings it skipped named beneath the offer.

        A run that skipped every recording it held has nothing to offer, so it reports the recordings
        it skipped and the converter returns to idle.
        """
        self._on_written()
        if success.skipped and not success.written:
            self._report_nothing_written(success)
            return

        if success.is_single:
            message = self._language_manager["main.converter.message.load_file_prompt"]
            ok_label = self._language_manager["main.converter.label.load_button"]
            path: Optional[Path] = success.written[0]
        else:
            message = self._language_manager["main.converter.message.load_directory_prompt"]
            ok_label = self._language_manager["main.converter.label.open_button"]
            path = None

        self._dialogs.show_confirmation(
            TAG_MAIN_CONVERTER_DIALOG_LOAD,
            self._with_skipped(message, success),
            self._language_manager["main.converter.title.load_dialog"],
            self._converter_logic.handle_load_request,
            ok_label=ok_label,
            cancel_label=self._language_manager["main.converter.label.close_button"],
            path=path,
            on_cancel=self._converter_logic.close,
        )

    def _report_nothing_written(self, success: ConversionSuccess) -> None:
        self._converter_logic.close()
        self._dialogs.show_info(
            self._notice_tag,
            self._with_skipped(self._language_manager["main.converter.message.nothing_written"], success),
            self._language_manager["main.converter.title.nothing_written_dialog"],
            modal=True,
        )

    def _with_skipped(self, message: str, success: ConversionSuccess) -> str:
        """``message`` followed by the paragraph naming the recordings the run skipped, where it skipped any."""
        notice = self._skipped_recording_messages.notice(success.skipped)
        if notice is None:
            return message

        return PARAGRAPH_BREAK.join((message, notice))
