from pathlib import Path
from typing import Callable, Final
from unittest.mock import MagicMock

import pytest

from sampletones_application.categories.skipped import ROW_BULLET
from sampletones_application.coordinators.tabs.main.prompts import ConversionPrompts
from sampletones_application.logic.main.converter.run import ConversionSuccess
from sampletones_application.tags.main import (
    TAG_MAIN_CONVERTER_DIALOG_CANCEL,
    TAG_MAIN_CONVERTER_DIALOG_LOAD,
    TAG_MAIN_CONVERTER_DIALOG_OVERWRITE_TARGET,
)
from tests.suite.language import FakeLanguageManager
from tests.suite.questions import dialogs_on_the_line

NOTICE_TAG: Final[str] = "main.converter.panel"
PROGRESS_TITLE_KEY: Final[str] = "main.converter.title.progress_dialog"
LOAD_FILE_MESSAGE_KEY: Final[str] = "main.converter.message.load_file_prompt"
LOAD_BUTTON_KEY: Final[str] = "main.converter.label.load_button"
OPEN_BUTTON_KEY: Final[str] = "main.converter.label.open_button"
CLOSE_BUTTON_KEY: Final[str] = "main.converter.label.close_button"
SKIPPED_HEADING_KEY: Final[str] = "main.converter.message.skipped_recording_heading"
NOTHING_WRITTEN_KEY: Final[str] = "main.converter.message.nothing_written"
NOTHING_WRITTEN_TITLE_KEY: Final[str] = "main.converter.title.nothing_written_dialog"
STOP_BUTTON_KEY: Final[str] = "main.converter.label.stop_button"
CONTINUE_BUTTON_KEY: Final[str] = "main.converter.label.continue_button"
OVERWRITE_TARGET_PROMPT_KEY: Final[str] = "main.converter.message.overwrite_target_prompt"
OVERWRITE_TARGET_BUTTON_KEY: Final[str] = "main.converter.label.overwrite_target_button"
OVERWRITE_TARGETS_PROMPT_KEY: Final[str] = "main.converter.message.overwrite_targets_prompt"
OVERWRITE_TARGETS_TITLE_KEY: Final[str] = "main.converter.title.overwrite_targets_dialog"
SKIPPED_RECORDING: Final[Path] = Path("/samples/broken.wav")


@pytest.fixture
def converter_logic() -> MagicMock:
    return MagicMock()


@pytest.fixture
def dialogs() -> MagicMock:
    return dialogs_on_the_line()


@pytest.fixture
def written() -> MagicMock:
    return MagicMock()


@pytest.fixture
def prompts(converter_logic: MagicMock, dialogs: MagicMock, written: MagicMock) -> ConversionPrompts:
    return ConversionPrompts(
        converter_logic,
        notice_tag=NOTICE_TAG,
        dialogs=dialogs,
        language_manager=FakeLanguageManager(),
        on_written=written,
    )


class TestConversionSuccessDialog:
    """A completed conversion refreshes the reconstruction trees, then offers to load the result;
    both the load and the dismiss choice return the converter to idle."""

    def test_file_success_refreshes_and_offers_to_load(
        self,
        prompts: ConversionPrompts,
        converter_logic: MagicMock,
        dialogs: MagicMock,
        written: MagicMock,
    ) -> None:
        output_path = Path("/reconstructions/kick.rcn")

        prompts.offer_written(ConversionSuccess(written=(output_path,), skipped=()))

        written.assert_called_once_with()
        dialogs.show_confirmation.assert_called_once()
        args, kwargs = dialogs.show_confirmation.call_args
        assert args[0] == TAG_MAIN_CONVERTER_DIALOG_LOAD
        assert args[1] == LOAD_FILE_MESSAGE_KEY
        assert args[3] == converter_logic.handle_load_request
        assert kwargs["ok_label"] == LOAD_BUTTON_KEY
        assert kwargs["cancel_label"] == CLOSE_BUTTON_KEY
        assert kwargs["path"] == output_path
        assert kwargs["on_cancel"] == converter_logic.close

    def test_a_batch_offers_to_open_the_folder(self, prompts: ConversionPrompts, dialogs: MagicMock) -> None:
        written = (Path("/reconstructions/kick.rcn"), Path("/reconstructions/snare.rcn"))

        prompts.offer_written(ConversionSuccess(written=written, skipped=()))

        _, kwargs = dialogs.show_confirmation.call_args
        assert kwargs["ok_label"] == OPEN_BUTTON_KEY
        assert kwargs["path"] is None

    def test_the_offer_names_the_recordings_the_run_skipped_beneath_it(
        self,
        prompts: ConversionPrompts,
        dialogs: MagicMock,
    ) -> None:
        prompts.offer_written(
            ConversionSuccess(written=(Path("/reconstructions/kick.rcn"),), skipped=(SKIPPED_RECORDING,))
        )

        args, _ = dialogs.show_confirmation.call_args
        assert args[1] == f"{LOAD_FILE_MESSAGE_KEY}\n\n{SKIPPED_HEADING_KEY}\n{ROW_BULLET}{SKIPPED_RECORDING.name}"

    def test_a_run_that_wrote_nothing_reports_what_it_skipped_and_offers_nothing(
        self,
        prompts: ConversionPrompts,
        converter_logic: MagicMock,
        dialogs: MagicMock,
        written: MagicMock,
    ) -> None:
        prompts.offer_written(ConversionSuccess(written=(), skipped=(SKIPPED_RECORDING,)))

        written.assert_called_once_with()
        dialogs.show_confirmation.assert_not_called()
        converter_logic.close.assert_called_once_with()
        args, kwargs = dialogs.show_info.call_args
        assert args[0] == NOTICE_TAG
        assert args[1] == f"{NOTHING_WRITTEN_KEY}\n\n{SKIPPED_HEADING_KEY}\n{ROW_BULLET}{SKIPPED_RECORDING.name}"
        assert args[2] == NOTHING_WRITTEN_TITLE_KEY
        assert kwargs["modal"] is True

    def test_a_run_that_wrote_nothing_and_skipped_nothing_still_offers_the_folder(
        self,
        prompts: ConversionPrompts,
        dialogs: MagicMock,
    ) -> None:
        prompts.offer_written(ConversionSuccess(written=(), skipped=()))

        dialogs.show_info.assert_not_called()
        _, kwargs = dialogs.show_confirmation.call_args
        assert kwargs["ok_label"] == OPEN_BUTTON_KEY


class TestCancelConfirmation:
    """Canceling is destructive, so the panel's cancel intent asks for confirmation before the
    conversion is actually stopped."""

    def test_cancel_request_confirms_before_stopping(
        self,
        prompts: ConversionPrompts,
        converter_logic: MagicMock,
        dialogs: MagicMock,
    ) -> None:
        prompts.confirm_cancel()

        converter_logic.cancel.assert_not_called()
        dialogs.show_confirmation.assert_called_once()
        args, kwargs = dialogs.show_confirmation.call_args
        assert args[0] == TAG_MAIN_CONVERTER_DIALOG_CANCEL
        assert args[3] == converter_logic.cancel
        assert kwargs["ok_label"] == STOP_BUTTON_KEY
        assert kwargs["cancel_label"] == CONTINUE_BUTTON_KEY


class TestOverwritePrompt:
    """A conversion that would replace a reconstruction already made is put to the reader first."""

    def test_the_prompt_names_the_file_it_would_replace(
        self,
        prompts: ConversionPrompts,
        dialogs: MagicMock,
        tmp_path: Path,
    ) -> None:
        target = tmp_path / "song.stn"

        prompts.confirm_overwriting((target,))

        args, kwargs = dialogs.show_confirmation.call_args
        assert args[0] == TAG_MAIN_CONVERTER_DIALOG_OVERWRITE_TARGET
        assert args[1] == OVERWRITE_TARGET_PROMPT_KEY
        assert kwargs["ok_label"] == OVERWRITE_TARGET_BUTTON_KEY
        assert kwargs["path"] == target

    def test_several_standing_reconstructions_are_all_put_to_the_reader(
        self,
        prompts: ConversionPrompts,
        dialogs: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Confirming writes over every one of them, so the prompt speaks for all of them."""
        targets = tuple(tmp_path / name for name in ("one.stn", "two.stn", "three.stn"))

        prompts.confirm_overwriting(targets)

        args, kwargs = dialogs.show_confirmation.call_args
        assert args[1] == OVERWRITE_TARGETS_PROMPT_KEY
        assert args[2] == OVERWRITE_TARGETS_TITLE_KEY
        assert kwargs["path"] is None

    def test_confirming_runs_the_conversion_it_asked_about(
        self,
        prompts: ConversionPrompts,
        converter_logic: MagicMock,
        dialogs: MagicMock,
        tmp_path: Path,
    ) -> None:
        prompts.confirm_overwriting((tmp_path / "song.stn",))
        dialogs.show_confirmation.call_args.args[3]()

        converter_logic.start_conversion.assert_called_once_with(confirmed=True)

    def test_declining_converts_nothing(
        self,
        prompts: ConversionPrompts,
        converter_logic: MagicMock,
        tmp_path: Path,
    ) -> None:
        prompts.confirm_overwriting((tmp_path / "song.stn",))

        converter_logic.start_conversion.assert_not_called()


class TestWhyAConversionCannotStart:
    @pytest.mark.parametrize(
        ("report", "message"),
        [
            (ConversionPrompts.report_no_files, "main.converter.message.status_no_files"),
            (ConversionPrompts.report_no_channels, "main.converter.message.status_no_channels"),
        ],
        ids=["no-files", "no-channels"],
    )
    def test_a_conversion_with_nothing_to_do_says_why_beside_the_converter(
        self,
        prompts: ConversionPrompts,
        dialogs: MagicMock,
        report: Callable[[ConversionPrompts], None],
        message: str,
    ) -> None:
        report(prompts)

        dialogs.show_info.assert_called_once_with(NOTICE_TAG, message, PROGRESS_TITLE_KEY)

    def test_a_failed_conversion_shows_its_error(self, prompts: ConversionPrompts, dialogs: MagicMock) -> None:
        failure = RuntimeError("worker died")

        prompts.report_error(failure)

        dialogs.show_error.assert_called_once_with(failure, "main.converter.message.status_error")
