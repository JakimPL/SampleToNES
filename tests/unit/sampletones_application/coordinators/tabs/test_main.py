from pathlib import Path
from typing import Final
from unittest.mock import MagicMock

import pytest

from sampletones_application.constants.conversion import MAX_STEM_SOURCES
from sampletones_application.coordinators.tabs.main import MainTabCoordinator
from sampletones_application.logic.main.converter import ConversionSuccess
from sampletones_application.tags.main import (
    TAG_MAIN_CONVERTER_DIALOG_CANCEL,
    TAG_MAIN_CONVERTER_DIALOG_LOAD,
    TAG_MAIN_CONVERTER_DIALOG_OVERWRITE_TARGET,
    TAG_MAIN_EXPLORER_DIALOG_CONVERTER_RUNNING,
)
from tests.suite.language import FakeLanguageManager

CONVERTER_RUNNING_MESSAGE_KEY: Final[str] = "main.explorer.message.converter_running_msg"
CONVERTER_RUNNING_TITLE_KEY: Final[str] = "main.explorer.title.converter_running_dialog"
LOAD_FILE_MESSAGE_KEY: Final[str] = "main.converter.message.load_file_prompt"
LOAD_BUTTON_KEY: Final[str] = "main.converter.label.load_button"
OPEN_BUTTON_KEY: Final[str] = "main.converter.label.open_button"
CLOSE_BUTTON_KEY: Final[str] = "main.converter.label.close_button"
STOP_BUTTON_KEY: Final[str] = "main.converter.label.stop_button"
CONTINUE_BUTTON_KEY: Final[str] = "main.converter.label.continue_button"


def _coordinator(*, operation_active: bool) -> MainTabCoordinator:
    """A coordinator with only the state the reconstruct guards touch, bypassing the heavy
    constructor."""
    coordinator = MainTabCoordinator.__new__(MainTabCoordinator)
    coordinator._is_operation_active = lambda: operation_active
    coordinator._dialogs = MagicMock()
    coordinator._language_manager = FakeLanguageManager()
    coordinator._on_reconstruct_file = MagicMock()
    coordinator._on_reconstruct_directory = MagicMock()
    coordinator._converter_logic = MagicMock()
    coordinator._converter_logic.stems_mode = False
    return coordinator


class TestConverterRunningNotice:
    """The busy-authority guard at the intent entry point: an active exclusive operation raises
    the converter-running notice and reports the caller must decline; an idle authority stays
    silent so the caller proceeds."""

    def test_active_operation_notifies_and_reports_true(self) -> None:
        coordinator = _coordinator(operation_active=True)

        assert coordinator._notify_converter_running() is True

        coordinator._dialogs.show_info.assert_called_once_with(
            TAG_MAIN_EXPLORER_DIALOG_CONVERTER_RUNNING,
            CONVERTER_RUNNING_MESSAGE_KEY,
            CONVERTER_RUNNING_TITLE_KEY,
        )

    def test_idle_reports_false_silently(self) -> None:
        coordinator = _coordinator(operation_active=False)

        assert coordinator._notify_converter_running() is False

        coordinator._dialogs.show_info.assert_not_called()


class TestReconstructGuards:
    """Reconstruction and conversion share the exclusive worker pool, so the reconstruct intents
    decline while an operation runs and delegate to the wired callbacks when idle."""

    def test_file_request_declines_while_an_operation_is_active(self) -> None:
        coordinator = _coordinator(operation_active=True)

        coordinator._request_reconstruct_file(Path("/audio/sample.wav"))

        coordinator._on_reconstruct_file.assert_not_called()
        coordinator._dialogs.show_info.assert_called_once()

    def test_file_request_delegates_when_idle(self) -> None:
        coordinator = _coordinator(operation_active=False)
        filepath = Path("/audio/sample.wav")

        coordinator._request_reconstruct_file(filepath)

        coordinator._on_reconstruct_file.assert_called_once_with(filepath)
        coordinator._dialogs.show_info.assert_not_called()

    def test_directory_request_declines_while_an_operation_is_active(self) -> None:
        coordinator = _coordinator(operation_active=True)

        coordinator._request_reconstruct_directory(Path("/audio"))

        coordinator._on_reconstruct_directory.assert_not_called()
        coordinator._dialogs.show_info.assert_called_once()

    def test_directory_request_delegates_when_idle(self) -> None:
        coordinator = _coordinator(operation_active=False)
        directory = Path("/audio")

        coordinator._request_reconstruct_directory(directory)

        coordinator._on_reconstruct_directory.assert_called_once_with(directory)
        coordinator._dialogs.show_info.assert_not_called()


def _success_coordinator() -> MainTabCoordinator:
    coordinator = MainTabCoordinator.__new__(MainTabCoordinator)
    coordinator._dialogs = MagicMock()
    coordinator._on_refresh_trees = MagicMock()
    coordinator._converter_logic = MagicMock()
    coordinator._language_manager = FakeLanguageManager()
    return coordinator


class TestConversionSuccessDialog:
    """A completed conversion refreshes the reconstruction trees, then offers to load the result;
    both the load and the dismiss choice return the converter to idle."""

    def test_file_success_refreshes_and_offers_to_load(self) -> None:
        coordinator = _success_coordinator()
        output_path = Path("/reconstructions/kick.rcn")

        coordinator._on_conversion_success(ConversionSuccess(written=(output_path,)))

        coordinator._on_refresh_trees.assert_called_once_with()
        coordinator._dialogs.show_confirmation.assert_called_once()
        args, kwargs = coordinator._dialogs.show_confirmation.call_args
        assert args[0] == TAG_MAIN_CONVERTER_DIALOG_LOAD
        assert args[1] == LOAD_FILE_MESSAGE_KEY
        assert args[3] == coordinator._converter_logic.handle_load_request
        assert kwargs["ok_label"] == LOAD_BUTTON_KEY
        assert kwargs["cancel_label"] == CLOSE_BUTTON_KEY
        assert kwargs["path"] == output_path
        assert kwargs["on_cancel"] == coordinator._converter_logic.close

    def test_a_batch_offers_to_open_the_folder(self) -> None:
        coordinator = _success_coordinator()
        written = (Path("/reconstructions/kick.rcn"), Path("/reconstructions/snare.rcn"))

        coordinator._on_conversion_success(ConversionSuccess(written=written))

        _, kwargs = coordinator._dialogs.show_confirmation.call_args
        assert kwargs["ok_label"] == OPEN_BUTTON_KEY
        assert kwargs["path"] is None


class TestCancelConfirmation:
    """Cancelling is destructive, so the panel's cancel intent asks for confirmation before the
    conversion is actually stopped."""

    def test_cancel_request_confirms_before_stopping(self) -> None:
        coordinator = MainTabCoordinator.__new__(MainTabCoordinator)
        coordinator._dialogs = MagicMock()
        coordinator._converter_logic = MagicMock()
        coordinator._language_manager = FakeLanguageManager()

        coordinator._request_cancel_confirmation()

        coordinator._converter_logic.cancel.assert_not_called()
        coordinator._dialogs.show_confirmation.assert_called_once()
        args, kwargs = coordinator._dialogs.show_confirmation.call_args
        assert args[0] == TAG_MAIN_CONVERTER_DIALOG_CANCEL
        assert args[3] == coordinator._converter_logic.cancel
        assert kwargs["ok_label"] == STOP_BUTTON_KEY
        assert kwargs["cancel_label"] == CONTINUE_BUTTON_KEY


DISCARD_STEMS_PROMPT_KEY: Final[str] = "main.converter.message.discard_stems_prompt"
DISCARD_STEMS_BUTTON_KEY: Final[str] = "main.converter.label.discard_stems_button"
KEEP_STEMS_BUTTON_KEY: Final[str] = "main.converter.label.keep_stems_button"


def _stems_coordinator(
    *,
    operation_active: bool = False,
    stems_mode: bool = True,
    source_count: int = 0,
    room: int = MAX_STEM_SOURCES,
) -> MainTabCoordinator:
    coordinator = MainTabCoordinator.__new__(MainTabCoordinator)
    coordinator._is_operation_active = lambda: operation_active
    coordinator._notify_converter_running = lambda: operation_active
    coordinator._dialogs = MagicMock()
    coordinator._language_manager = FakeLanguageManager()
    coordinator._converter_logic = MagicMock()
    coordinator._converter_logic.stems_mode = stems_mode
    coordinator._converter_logic.source_count = source_count
    coordinator._converter_logic.room_for_sources = room
    coordinator._stem_selection_window = MagicMock()
    return coordinator


class TestStemsModeSwitch:
    """Leaving stems mode drops every recording but the first, so a list of several asks first."""

    def test_entering_stems_mode_takes_effect_at_once(self) -> None:
        coordinator = _stems_coordinator(stems_mode=False)

        coordinator._request_stems_mode(True)

        coordinator._converter_logic.set_stems_mode.assert_called_once_with(True)
        coordinator._dialogs.show_confirmation.assert_not_called()

    def test_leaving_with_one_recording_takes_effect_at_once(self) -> None:
        coordinator = _stems_coordinator(source_count=1)

        coordinator._request_stems_mode(False)

        coordinator._converter_logic.set_stems_mode.assert_called_once_with(False)
        coordinator._dialogs.show_confirmation.assert_not_called()

    def test_leaving_with_several_recordings_asks_first(self) -> None:
        coordinator = _stems_coordinator(source_count=3)

        coordinator._request_stems_mode(False)

        coordinator._converter_logic.set_stems_mode.assert_not_called()
        args, kwargs = coordinator._dialogs.show_confirmation.call_args
        assert args[1] == DISCARD_STEMS_PROMPT_KEY
        assert kwargs["ok_label"] == DISCARD_STEMS_BUTTON_KEY
        assert kwargs["cancel_label"] == KEEP_STEMS_BUTTON_KEY

    def test_confirming_the_prompt_leaves_stems_mode(self) -> None:
        coordinator = _stems_coordinator(source_count=3)

        coordinator._request_stems_mode(False)
        args, _ = coordinator._dialogs.show_confirmation.call_args
        args[3]()

        coordinator._converter_logic.set_stems_mode.assert_called_once_with(False)

    def test_declining_the_prompt_repaints_the_checkbox(self) -> None:
        """The checkbox already moved when it was clicked, so declining restores what stands."""
        coordinator = _stems_coordinator(source_count=3)

        coordinator._request_stems_mode(False)
        _, kwargs = coordinator._dialogs.show_confirmation.call_args
        kwargs["on_cancel"]()

        coordinator._converter_logic.set_stems_mode.assert_not_called()
        coordinator._converter_logic.refresh_view.assert_called_once_with()


class TestDirectoryAdd:
    """Ctrl-clicking a folder offers its recordings; a folder that overflows the list asks which."""

    def test_a_folder_that_fits_is_added_whole(self, tmp_path: Path) -> None:
        (tmp_path / "a.wav").touch()
        (tmp_path / "b.wav").touch()
        coordinator = _stems_coordinator(room=MAX_STEM_SOURCES)

        coordinator._on_directory_add_requested(tmp_path)

        added = coordinator._converter_logic.add_sources.call_args.args[0]
        assert {path.name for path in added} == {"a.wav", "b.wav"}
        coordinator._stem_selection_window.open.assert_not_called()

    def test_a_folder_that_overflows_raises_the_selection(self, tmp_path: Path) -> None:
        for index in range(3):
            (tmp_path / f"{index}.wav").touch()
        coordinator = _stems_coordinator(room=2)

        coordinator._on_directory_add_requested(tmp_path)

        coordinator._converter_logic.add_sources.assert_not_called()
        candidates, room = coordinator._stem_selection_window.open.call_args.args
        assert len(candidates) == 3
        assert room == 2

    def test_a_folder_holding_no_recordings_is_left_alone(self, tmp_path: Path) -> None:
        (tmp_path / "notes.txt").write_text("not audio")
        coordinator = _stems_coordinator()

        coordinator._on_directory_add_requested(tmp_path)

        coordinator._converter_logic.add_sources.assert_not_called()
        coordinator._stem_selection_window.open.assert_not_called()

    def test_a_classic_conversion_starts_gathering(self, tmp_path: Path) -> None:
        """The gesture is what starts a stems conversion, so it turns the mode on to answer."""
        (tmp_path / "a.wav").touch()
        coordinator = _stems_coordinator(stems_mode=False)

        coordinator._on_directory_add_requested(tmp_path)

        coordinator._converter_logic.set_stems_mode.assert_called_once_with(True)
        assert coordinator._converter_logic.add_sources.call_args.args[0][0].name == "a.wav"

    def test_a_busy_application_ignores_the_gesture(self, tmp_path: Path) -> None:
        (tmp_path / "a.wav").touch()
        coordinator = _stems_coordinator(operation_active=True)

        coordinator._on_directory_add_requested(tmp_path)

        coordinator._converter_logic.add_sources.assert_not_called()


class TestFileAdd:
    """A recording added from the browser's menu joins a stems list, opening one where none stands."""

    def test_a_recording_joins_the_list(self, tmp_path: Path) -> None:
        recording = tmp_path / "bass.wav"
        recording.touch()
        coordinator = _stems_coordinator()

        coordinator._on_file_add_requested(recording)

        coordinator._converter_logic.add_sources.assert_called_once_with([recording])

    def test_adding_from_a_classic_conversion_turns_stems_mode_on(self, tmp_path: Path) -> None:
        recording = tmp_path / "bass.wav"
        recording.touch()
        coordinator = _stems_coordinator(stems_mode=False)

        coordinator._on_file_add_requested(recording)

        coordinator._converter_logic.set_stems_mode.assert_called_once_with(True)

    def test_a_busy_application_ignores_the_gesture(self, tmp_path: Path) -> None:
        coordinator = _stems_coordinator(operation_active=True)

        coordinator._on_file_add_requested(tmp_path / "bass.wav")

        coordinator._converter_logic.add_sources.assert_not_called()


class TestModifierAddAvailability:
    """The modifier click gathers a recording whenever the converter is free to take one."""

    def test_a_gathered_list_takes_the_click(self) -> None:
        assert _stems_coordinator()._can_add_stems() is True

    def test_a_classic_conversion_takes_the_click_and_opens_a_list(self) -> None:
        assert _stems_coordinator(stems_mode=False)._can_add_stems() is True

    def test_a_busy_application_leaves_the_click_alone(self) -> None:
        assert _stems_coordinator(operation_active=True)._can_add_stems() is False


OVERWRITE_TARGET_PROMPT_KEY: Final[str] = "main.converter.message.overwrite_target_prompt"
OVERWRITE_TARGET_BUTTON_KEY: Final[str] = "main.converter.label.overwrite_target_button"


class TestOverwritePrompt:
    """A conversion that would replace a reconstruction already made is put to the reader first."""

    def test_the_prompt_names_the_file_it_would_replace(self, tmp_path: Path) -> None:
        coordinator = _stems_coordinator()
        target = tmp_path / "song.stn"

        coordinator._confirm_overwriting_target(target)

        args, kwargs = coordinator._dialogs.show_confirmation.call_args
        assert args[0] == TAG_MAIN_CONVERTER_DIALOG_OVERWRITE_TARGET
        assert args[1] == OVERWRITE_TARGET_PROMPT_KEY
        assert kwargs["ok_label"] == OVERWRITE_TARGET_BUTTON_KEY
        assert kwargs["path"] == target

    def test_confirming_runs_the_conversion_it_asked_about(self, tmp_path: Path) -> None:
        coordinator = _stems_coordinator()

        coordinator._confirm_overwriting_target(tmp_path / "song.stn")
        coordinator._dialogs.show_confirmation.call_args.args[3]()

        coordinator._converter_logic.start_conversion.assert_called_once_with(confirmed=True)

    def test_declining_converts_nothing(self, tmp_path: Path) -> None:
        coordinator = _stems_coordinator()

        coordinator._confirm_overwriting_target(tmp_path / "song.stn")

        coordinator._converter_logic.start_conversion.assert_not_called()


class TestReconstructLeavesStemsMode:
    """A Reconstruct names what a classic conversion converts, so a gathered list is asked about."""

    def _coordinator(self, *, stems_mode: bool) -> MainTabCoordinator:
        coordinator = _stems_coordinator(stems_mode=stems_mode)
        coordinator._on_reconstruct_file = MagicMock()
        coordinator._on_reconstruct_directory = MagicMock()
        return coordinator

    def test_a_classic_conversion_reconstructs_straight_away(self, tmp_path: Path) -> None:
        coordinator = self._coordinator(stems_mode=False)

        coordinator._request_reconstruct_file(tmp_path / "a.wav")

        coordinator._on_reconstruct_file.assert_called_once_with(tmp_path / "a.wav")
        coordinator._dialogs.show_confirmation.assert_not_called()

    @pytest.mark.parametrize("gesture", ["_request_reconstruct_file", "_request_reconstruct_directory"])
    def test_a_gathered_list_is_asked_about_first(self, tmp_path: Path, gesture: str) -> None:
        coordinator = self._coordinator(stems_mode=True)

        getattr(coordinator, gesture)(tmp_path)

        coordinator._on_reconstruct_file.assert_not_called()
        coordinator._on_reconstruct_directory.assert_not_called()
        assert coordinator._dialogs.show_confirmation.call_args.args[1] == DISCARD_STEMS_PROMPT_KEY

    def test_confirming_leaves_stems_mode_and_converts(self, tmp_path: Path) -> None:
        coordinator = self._coordinator(stems_mode=True)

        coordinator._request_reconstruct_directory(tmp_path)
        coordinator._dialogs.show_confirmation.call_args.args[3]()

        coordinator._converter_logic.set_stems_mode.assert_called_once_with(False)
        coordinator._on_reconstruct_directory.assert_called_once_with(tmp_path)

    def test_declining_converts_nothing(self, tmp_path: Path) -> None:
        coordinator = self._coordinator(stems_mode=True)

        coordinator._request_reconstruct_directory(tmp_path)
        coordinator._dialogs.show_confirmation.call_args.kwargs["on_cancel"]()

        coordinator._converter_logic.set_stems_mode.assert_not_called()
        coordinator._on_reconstruct_directory.assert_not_called()
