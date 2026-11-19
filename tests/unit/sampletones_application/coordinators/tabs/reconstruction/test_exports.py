from pathlib import Path
from typing import Final, Optional
from unittest.mock import MagicMock

import pytest

from sampletones_application.categories.export import ExportMessages
from sampletones_application.categories.manager import LanguageManager
from sampletones_application.coordinators.tabs.reconstruction.exports import ReconstructionExports
from sampletones_application.paths import LANG_EN
from sampletones_application.services.export.error import ExportError
from sampletones_application.services.export.kind import ExportKind
from sampletones_application.services.export.success import ExportSuccess
from sampletones_core.constants.enums import ChannelName
from sampletones_core.exporters.skipped import NO_SKIPPED_ROWS
from sampletones_core.exporters.truncation import EnvelopeTruncation
from sampletones_core.exports.format import ExportFormat

LANGUAGE_MANAGER: Final[LanguageManager] = LanguageManager(LANG_EN)
MESSAGES: Final[ExportMessages] = ExportMessages.build(LANGUAGE_MANAGER)


@pytest.fixture
def dialogs() -> MagicMock:
    return MagicMock()


@pytest.fixture
def panel_logic() -> MagicMock:
    return MagicMock()


@pytest.fixture
def instrument_editor() -> MagicMock:
    editor = MagicMock()
    editor.instrument = None
    return editor


@pytest.fixture
def instrument_exports() -> MagicMock:
    return MagicMock()


@pytest.fixture
def format_setup() -> MagicMock:
    return MagicMock()


@pytest.fixture
def exports(
    panel_logic: MagicMock,
    instrument_editor: MagicMock,
    instrument_exports: MagicMock,
    format_setup: MagicMock,
    dialogs: MagicMock,
) -> ReconstructionExports:
    """The exports, with a setup of its own for Bitphase alone."""
    return ReconstructionExports(
        panel_logic,
        instrument_editor,
        instrument_exports,
        {},
        {ExportFormat.BITPHASE: format_setup},
        dialogs=dialogs,
        language_manager=LANGUAGE_MANAGER,
    )


def _shown_message(dialogs: MagicMock) -> str:
    _, message, _ = dialogs.show_message_with_path.call_args.args
    return str(message)


def _success(kind: ExportKind, truncation: Optional[EnvelopeTruncation]) -> ExportSuccess:
    return ExportSuccess(
        kind=kind,
        filepath=Path("written"),
        export_format=None if kind is ExportKind.WAV else ExportFormat.FAMITRACKER,
        truncation=truncation,
        skipped_rows=NO_SKIPPED_ROWS,
    )


class TestExportingTheInstrumentInFront:
    """Whatever the tab holds reaches a file the same way, so a pool voice is written by voice."""

    def test_an_instrument_is_written_by_the_voice_it_is(
        self,
        exports: ReconstructionExports,
        instrument_editor: MagicMock,
        instrument_exports: MagicMock,
        panel_logic: MagicMock,
    ) -> None:
        """The sequencer's menu and this button name the same voice, so they write the same file."""
        instrument_editor.instrument = MagicMock(id="lead-id")

        exports.export_instrument(ChannelName.PULSE1)

        instrument_exports.request_voice.assert_called_once_with("lead-id", None)
        panel_logic.exportable_instrument.assert_not_called()

    def test_a_reconstructions_slice_is_written_as_the_tab_holds_it(
        self,
        exports: ReconstructionExports,
        instrument_exports: MagicMock,
        panel_logic: MagicMock,
    ) -> None:
        exportable = panel_logic.exportable_instrument.return_value

        exports.export_instrument(ChannelName.TRIANGLE)

        panel_logic.exportable_instrument.assert_called_once_with(ChannelName.TRIANGLE)
        instrument_exports.request.assert_called_once_with(exportable.source, exportable.name)

    def test_a_channel_describing_no_frame_is_written_nowhere(
        self,
        exports: ReconstructionExports,
        instrument_exports: MagicMock,
        panel_logic: MagicMock,
    ) -> None:
        panel_logic.exportable_instrument.return_value = None

        exports.export_instrument(ChannelName.NOISE)

        instrument_exports.request.assert_not_called()
        instrument_exports.request_voice.assert_not_called()


class TestAskingForTheInstruments:
    """A format with a setup of its own opens it; any other asks for the destination alone."""

    def test_a_format_with_a_setup_opens_it_for_the_open_document(
        self,
        exports: ReconstructionExports,
        panel_logic: MagicMock,
        format_setup: MagicMock,
    ) -> None:
        exports.request_instruments(ExportFormat.BITPHASE)

        format_setup.open_sample.assert_called_once_with(ExportFormat.BITPHASE, panel_logic.sample_request.return_value)
        panel_logic.request_export_instruments_dialog.assert_not_called()

    def test_a_format_with_a_setup_and_nothing_open_opens_nothing(
        self,
        exports: ReconstructionExports,
        panel_logic: MagicMock,
        format_setup: MagicMock,
    ) -> None:
        panel_logic.sample_request.return_value = None

        exports.request_instruments(ExportFormat.BITPHASE)

        format_setup.open_sample.assert_not_called()
        panel_logic.request_export_instruments_dialog.assert_not_called()

    def test_a_format_without_a_setup_asks_for_the_destination(
        self,
        exports: ReconstructionExports,
        panel_logic: MagicMock,
        format_setup: MagicMock,
    ) -> None:
        exports.request_instruments(ExportFormat.FAMITRACKER)

        panel_logic.request_export_instruments_dialog.assert_called_once_with(ExportFormat.FAMITRACKER)
        format_setup.open_sample.assert_not_called()


class TestExportResultReportsTruncation:
    def test_a_complete_instrument_export_shows_the_success_message(
        self,
        exports: ReconstructionExports,
        dialogs: MagicMock,
    ) -> None:
        exports.report(_success(ExportKind.INSTRUMENT, None))

        assert _shown_message(dialogs) == MESSAGES.instrument_success

    def test_a_shortened_instrument_export_names_both_frame_counts(
        self,
        exports: ReconstructionExports,
        dialogs: MagicMock,
    ) -> None:
        exports.report(
            _success(ExportKind.INSTRUMENT, EnvelopeTruncation(frames=252, source_frames=300, instruments=1))
        )

        message = _shown_message(dialogs)
        assert message.startswith(MESSAGES.instrument_success)
        assert "300" in message
        assert "252" in message

    def test_a_shortened_reconstruction_export_counts_the_instruments(
        self,
        exports: ReconstructionExports,
        dialogs: MagicMock,
    ) -> None:
        exports.report(_success(ExportKind.SAMPLE, EnvelopeTruncation(frames=252, source_frames=410, instruments=3)))

        message = _shown_message(dialogs)
        assert message.startswith(MESSAGES.instruments_success)
        assert "3" in message

    def test_a_wav_export_shows_its_own_message(self, exports: ReconstructionExports, dialogs: MagicMock) -> None:
        exports.report(_success(ExportKind.WAV, None))

        assert _shown_message(dialogs) == MESSAGES.wav_success

    def test_a_dropped_wav_export_shows_its_own_message(
        self,
        exports: ReconstructionExports,
        dialogs: MagicMock,
    ) -> None:
        exports.report_dropped(Path("track.wav"))

        assert _shown_message(dialogs) == MESSAGES.wav_dropped

    @pytest.mark.parametrize(
        ("kind", "message"),
        [
            (ExportKind.WAV, MESSAGES.wav_failed),
            (ExportKind.INSTRUMENT, MESSAGES.instrument_failed),
            (ExportKind.SAMPLE, MESSAGES.instruments_failed),
        ],
    )
    def test_a_failed_export_names_what_it_failed_to_write(
        self,
        exports: ReconstructionExports,
        dialogs: MagicMock,
        kind: ExportKind,
        message: str,
    ) -> None:
        failure = OSError("disk full")

        exports.report(
            ExportError(
                kind=kind,
                export_format=None if kind is ExportKind.WAV else ExportFormat.FAMITRACKER,
                exception=failure,
            )
        )

        dialogs.show_error.assert_called_once_with(failure, message)
        dialogs.show_message_with_path.assert_not_called()
