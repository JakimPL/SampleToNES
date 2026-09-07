from pathlib import Path
from typing import Final, Tuple
from unittest.mock import MagicMock

import pytest

from sampletones_application.constants.conversion import MAX_STEM_SOURCES
from sampletones_application.constants.output import OutputKind
from sampletones_application.coordinators.tabs.hooks import MainTabHooks
from sampletones_application.coordinators.tabs.main import MainTabCoordinator
from sampletones_application.logic.main.converter.run import ConversionSuccess
from sampletones_application.logic.main.sources.scan import FolderScan
from sampletones_application.tags.main import (
    TAG_MAIN_CONVERTER_DIALOG_CANCEL,
    TAG_MAIN_CONVERTER_DIALOG_LOAD,
    TAG_MAIN_CONVERTER_DIALOG_OVERWRITE_TARGET,
    TAG_MAIN_EXPLORER_DIALOG_CONVERTER_RUNNING,
)
from sampletones_application.utils.parallelization.thread import SingleThreadExecutor
from tests.suite.language import FakeLanguageManager

CONVERTER_RUNNING_MESSAGE_KEY: Final[str] = "main.explorer.message.converter_running_msg"
CONVERTER_RUNNING_TITLE_KEY: Final[str] = "main.explorer.title.converter_running_dialog"
LOAD_FILE_MESSAGE_KEY: Final[str] = "main.converter.message.load_file_prompt"
LOAD_BUTTON_KEY: Final[str] = "main.converter.label.load_button"
OPEN_BUTTON_KEY: Final[str] = "main.converter.label.open_button"
CLOSE_BUTTON_KEY: Final[str] = "main.converter.label.close_button"
STOP_BUTTON_KEY: Final[str] = "main.converter.label.stop_button"
CONTINUE_BUTTON_KEY: Final[str] = "main.converter.label.continue_button"


def _hooks(*, operation_active: bool) -> MainTabHooks:
    """The tab's outward collaborator, every hook of which a test can read what reached it."""
    return MainTabHooks(
        is_operation_active=lambda: operation_active,
        on_busy_state_changed=MagicMock(),
        on_reconstruct_file=MagicMock(),
        on_reconstruct_directory=MagicMock(),
        on_load_reconstruction=MagicMock(),
        on_load_library=MagicMock(),
        on_load_file=MagicMock(),
        on_load_directory=MagicMock(),
        on_canceled=MagicMock(),
        on_refresh_trees=MagicMock(),
        on_generate_library=MagicMock(),
    )


def _coordinator(*, operation_active: bool) -> MainTabCoordinator:
    """A coordinator with only the state the reconstruct guards touch, bypassing the heavy
    constructor."""
    coordinator = MainTabCoordinator.__new__(MainTabCoordinator)
    coordinator._hooks = _hooks(operation_active=operation_active)
    coordinator._dialogs = MagicMock()
    coordinator._language_manager = FakeLanguageManager()
    coordinator._converter_logic = MagicMock()
    coordinator._converter_logic.mixes = False
    coordinator._converter_logic.gathered_paths = ()
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

        coordinator._hooks.on_reconstruct_file.assert_not_called()
        coordinator._dialogs.show_info.assert_called_once()

    def test_file_request_delegates_when_idle(self) -> None:
        coordinator = _coordinator(operation_active=False)
        filepath = Path("/audio/sample.wav")

        coordinator._request_reconstruct_file(filepath)

        coordinator._hooks.on_reconstruct_file.assert_called_once_with(filepath)
        coordinator._dialogs.show_info.assert_not_called()

    def test_directory_request_declines_while_an_operation_is_active(self) -> None:
        coordinator = _coordinator(operation_active=True)

        coordinator._request_reconstruct_directory(Path("/audio"))

        coordinator._hooks.on_reconstruct_directory.assert_not_called()
        coordinator._dialogs.show_info.assert_called_once()

    def test_directory_request_delegates_when_idle(self) -> None:
        coordinator = _coordinator(operation_active=False)
        directory = Path("/audio")

        coordinator._request_reconstruct_directory(directory)

        coordinator._hooks.on_reconstruct_directory.assert_called_once_with(directory)
        coordinator._dialogs.show_info.assert_not_called()


def _success_coordinator() -> MainTabCoordinator:
    coordinator = MainTabCoordinator.__new__(MainTabCoordinator)
    coordinator._dialogs = MagicMock()
    coordinator._hooks = _hooks(operation_active=False)
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

        coordinator._hooks.on_refresh_trees.assert_called_once_with()
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
    mixes: bool = True,
    gathered: Tuple[Path, ...] = (),
    folder_rows: Tuple[MagicMock, ...] = (),
    gathered_rows: Tuple[MagicMock, ...] = (),
    room: int = MAX_STEM_SOURCES,
    ceiling: int = MAX_STEM_SOURCES,
) -> MainTabCoordinator:
    coordinator = MainTabCoordinator.__new__(MainTabCoordinator)
    coordinator._hooks = _hooks(operation_active=operation_active)
    coordinator._notify_converter_running = lambda: operation_active
    coordinator._dialogs = MagicMock()
    coordinator._language_manager = FakeLanguageManager()
    coordinator._converter_logic = MagicMock()
    coordinator._converter_logic.mixes = mixes
    coordinator._converter_logic.gathered_paths = gathered
    coordinator._converter_logic.source_count = len(gathered)
    coordinator._converter_logic.room_for_sources = room
    coordinator._converter_logic.mix_ceiling = ceiling
    coordinator._converter_logic.list_fits_a_mix = len(gathered) <= ceiling
    coordinator._converter_logic.rows_offered.return_value = folder_rows
    coordinator._converter_logic.gathered_rows = gathered_rows
    coordinator._stem_selection_window = MagicMock()
    coordinator._scan_window = MagicMock()
    coordinator._repaint_priority = 0
    coordinator._folder_scan = FolderScan()
    coordinator._folder_scan.on_started = coordinator._on_scan_started
    coordinator._folder_scan.on_progress = coordinator._on_scan_progress
    coordinator._folder_scan.on_stopped = coordinator._on_scan_stopped
    return coordinator


def _folder_of(tmp_path: Path, count: int) -> Path:
    """A folder holding that many recordings, which the reading below it finds."""
    root = tmp_path / "takes"
    root.mkdir(exist_ok=True)
    for index in range(count):
        (root / f"take_{index:02d}.wav").touch()

    return root


def _add_folder(coordinator: MainTabCoordinator, root: Path) -> None:
    """Asks for the folder and waits for the reading, the way a reader does."""
    coordinator._on_directory_add_requested(root)
    SingleThreadExecutor.join_all()


class TestOutputSwitch:
    """A mix reaches a fixed number of recordings, so a longer list is put to the reader first."""

    def test_turning_to_a_mix_takes_effect_at_once(self) -> None:
        coordinator = _stems_coordinator(mixes=False)

        coordinator._request_output(OutputKind.MIXED)

        coordinator._converter_logic.set_output.assert_called_once_with(OutputKind.MIXED)
        coordinator._dialogs.show_confirmation.assert_not_called()

    def test_turning_away_from_a_mix_takes_effect_at_once(self) -> None:
        coordinator = _stems_coordinator(gathered=tuple(Path(f"/audio/{index}.wav") for index in range(20)))

        coordinator._request_output(OutputKind.PER_RECORDING)

        coordinator._converter_logic.set_output.assert_called_once_with(OutputKind.PER_RECORDING)
        coordinator._dialogs.show_confirmation.assert_not_called()

    def test_a_list_longer_than_a_mix_holds_asks_which_to_mix(self) -> None:
        gathered = tuple(Path(f"/audio/{index}.wav") for index in range(MAX_STEM_SOURCES + 2))
        listed = _rows_holding(*[1] * len(gathered))
        coordinator = _stems_coordinator(mixes=False, gathered=gathered, gathered_rows=listed)

        coordinator._request_output(OutputKind.MIXED)

        coordinator._converter_logic.set_output.assert_not_called()
        rows, room, answer = coordinator._stem_selection_window.open.call_args.args
        assert rows == listed
        assert room == MAX_STEM_SOURCES
        assert answer == coordinator._converter_logic.mix_only

    def test_a_list_a_mix_holds_takes_effect_at_once(self) -> None:
        gathered = tuple(Path(f"/audio/{index}.wav") for index in range(MAX_STEM_SOURCES))
        coordinator = _stems_coordinator(mixes=False, gathered=gathered)

        coordinator._request_output(OutputKind.MIXED)

        coordinator._converter_logic.set_output.assert_called_once_with(OutputKind.MIXED)
        coordinator._stem_selection_window.open.assert_not_called()


class TestDirectoryAdd:
    """Ctrl-clicking a folder gathers it, standing for the recordings found below it."""

    def test_a_folder_joins_the_setup(self, tmp_path: Path) -> None:
        coordinator = _stems_coordinator(mixes=False)
        root = _folder_of(tmp_path, 2)

        _add_folder(coordinator, root)

        gathered, found = coordinator._converter_logic.gather_folder.call_args.args
        assert gathered == root
        assert {path.name for path in found} == {"take_00.wav", "take_01.wav"}

    def test_a_busy_application_ignores_the_gesture(self, tmp_path: Path) -> None:
        coordinator = _stems_coordinator(operation_active=True)

        coordinator._on_directory_add_requested(tmp_path)

        coordinator._converter_logic.gather_folder.assert_not_called()


class TestFileAdd:
    """A recording added from the browser's menu joins the setup, whichever run it names."""

    def test_a_recording_joins_the_list(self, tmp_path: Path) -> None:
        recording = tmp_path / "bass.wav"
        recording.touch()
        coordinator = _stems_coordinator()

        coordinator._on_file_add_requested(recording)

        coordinator._converter_logic.gather_recordings.assert_called_once_with([recording])

    def test_a_busy_application_ignores_the_gesture(self, tmp_path: Path) -> None:
        coordinator = _stems_coordinator(operation_active=True)

        coordinator._on_file_add_requested(tmp_path / "bass.wav")

        coordinator._converter_logic.gather_recordings.assert_not_called()


class TestModifierAddAvailability:
    """The modifier click gathers a recording whenever the converter is free to take one."""

    def test_a_gathered_list_takes_the_click(self) -> None:
        assert _stems_coordinator()._can_add_stems() is True

    def test_a_classic_conversion_takes_the_click_and_opens_a_list(self) -> None:
        assert _stems_coordinator(mixes=False)._can_add_stems() is True

    def test_a_busy_application_leaves_the_click_alone(self) -> None:
        assert _stems_coordinator(operation_active=True)._can_add_stems() is False


OVERWRITE_TARGET_PROMPT_KEY: Final[str] = "main.converter.message.overwrite_target_prompt"
OVERWRITE_TARGET_BUTTON_KEY: Final[str] = "main.converter.label.overwrite_target_button"
OVERWRITE_TARGETS_PROMPT_KEY: Final[str] = "main.converter.message.overwrite_targets_prompt"
OVERWRITE_TARGETS_TITLE_KEY: Final[str] = "main.converter.title.overwrite_targets_dialog"


class TestOverwritePrompt:
    """A conversion that would replace a reconstruction already made is put to the reader first."""

    def test_the_prompt_names_the_file_it_would_replace(self, tmp_path: Path) -> None:
        coordinator = _stems_coordinator()
        target = tmp_path / "song.stn"

        coordinator._confirm_overwriting_target((target,))

        args, kwargs = coordinator._dialogs.show_confirmation.call_args
        assert args[0] == TAG_MAIN_CONVERTER_DIALOG_OVERWRITE_TARGET
        assert args[1] == OVERWRITE_TARGET_PROMPT_KEY
        assert kwargs["ok_label"] == OVERWRITE_TARGET_BUTTON_KEY
        assert kwargs["path"] == target

    def test_several_standing_reconstructions_are_all_put_to_the_reader(self, tmp_path: Path) -> None:
        """Confirming writes over every one of them, so the prompt speaks for all of them."""
        coordinator = _stems_coordinator()
        targets = tuple(tmp_path / name for name in ("one.stn", "two.stn", "three.stn"))

        coordinator._confirm_overwriting_target(targets)

        args, kwargs = coordinator._dialogs.show_confirmation.call_args
        assert args[1] == OVERWRITE_TARGETS_PROMPT_KEY
        assert args[2] == OVERWRITE_TARGETS_TITLE_KEY
        assert kwargs["path"] is None

    def test_confirming_runs_the_conversion_it_asked_about(self, tmp_path: Path) -> None:
        coordinator = _stems_coordinator()

        coordinator._confirm_overwriting_target((tmp_path / "song.stn",))
        coordinator._dialogs.show_confirmation.call_args.args[3]()

        coordinator._converter_logic.start_conversion.assert_called_once_with(confirmed=True)

    def test_declining_converts_nothing(self, tmp_path: Path) -> None:
        coordinator = _stems_coordinator()

        coordinator._confirm_overwriting_target((tmp_path / "song.stn",))

        coordinator._converter_logic.start_conversion.assert_not_called()


class TestReconstructReplacesTheSetup:
    """A Reconstruct converts what it names alone, so a setup already holding sources is asked about."""

    def _coordinator(self, *, mixes: bool, gathered: Tuple[Path, ...] = ()) -> MainTabCoordinator:
        return _stems_coordinator(mixes=mixes, gathered=gathered)

    def test_an_empty_setup_reconstructs_straight_away(self, tmp_path: Path) -> None:
        coordinator = self._coordinator(mixes=False)

        coordinator._request_reconstruct_file(tmp_path / "a.wav")

        coordinator._hooks.on_reconstruct_file.assert_called_once_with(tmp_path / "a.wav")
        coordinator._dialogs.show_confirmation.assert_not_called()

    @pytest.mark.parametrize("gesture", ["_request_reconstruct_file", "_request_reconstruct_directory"])
    def test_a_gathered_list_is_asked_about_first(self, tmp_path: Path, gesture: str) -> None:
        coordinator = self._coordinator(mixes=True, gathered=(Path("/audio/a.wav"),))

        getattr(coordinator, gesture)(tmp_path)

        coordinator._hooks.on_reconstruct_file.assert_not_called()
        coordinator._hooks.on_reconstruct_directory.assert_not_called()
        assert coordinator._dialogs.show_confirmation.call_args.args[1] == DISCARD_STEMS_PROMPT_KEY

    def test_confirming_converts_what_was_named(self, tmp_path: Path) -> None:
        coordinator = self._coordinator(mixes=True, gathered=(Path("/audio/a.wav"),))

        coordinator._request_reconstruct_directory(tmp_path)
        coordinator._dialogs.show_confirmation.call_args.args[3]()

        coordinator._hooks.on_reconstruct_directory.assert_called_once_with(tmp_path)

    def test_declining_converts_nothing(self, tmp_path: Path) -> None:
        coordinator = self._coordinator(mixes=True, gathered=(Path("/audio/a.wav"),))

        coordinator._request_reconstruct_directory(tmp_path)
        coordinator._dialogs.show_confirmation.call_args.kwargs["on_cancel"]()

        coordinator._converter_logic.set_output.assert_not_called()
        coordinator._hooks.on_reconstruct_directory.assert_not_called()


def _rows_holding(*counts: int) -> Tuple[MagicMock, ...]:
    """Rows standing for that many recordings each, which is what the room is counted against."""
    return tuple(MagicMock(recordings=tuple(MagicMock() for _ in range(count))) for count in counts)


class TestGatheringAFolder:
    """A mix reaches a fixed number of recordings, so a folder overflowing it asks rather than gathers."""

    def test_a_run_writing_one_apiece_gathers_whatever_it_holds(self, tmp_path: Path) -> None:
        coordinator = _stems_coordinator(mixes=False, folder_rows=_rows_holding(MAX_STEM_SOURCES + 5))

        _add_folder(coordinator, _folder_of(tmp_path, MAX_STEM_SOURCES + 5))

        coordinator._converter_logic.gather_folder.assert_called_once()
        coordinator._stem_selection_window.open.assert_not_called()

    def test_a_folder_a_mix_still_holds_is_gathered(self, tmp_path: Path) -> None:
        coordinator = _stems_coordinator(mixes=True, folder_rows=_rows_holding(MAX_STEM_SOURCES))

        _add_folder(coordinator, _folder_of(tmp_path, MAX_STEM_SOURCES))

        coordinator._converter_logic.gather_folder.assert_called_once()
        coordinator._stem_selection_window.open.assert_not_called()

    def test_a_folder_overflowing_the_mix_asks_which_to_mix(self, tmp_path: Path) -> None:
        rows = _rows_holding(MAX_STEM_SOURCES, 1)
        coordinator = _stems_coordinator(mixes=True, folder_rows=rows)

        _add_folder(coordinator, _folder_of(tmp_path, MAX_STEM_SOURCES + 1))

        coordinator._converter_logic.gather_folder.assert_not_called()
        offered, room, answer = coordinator._stem_selection_window.open.call_args.args
        assert offered == coordinator._converter_logic.gathered_rows + rows
        assert room == MAX_STEM_SOURCES
        assert answer == coordinator._converter_logic.mix_only

    def test_a_full_mix_is_offered_beside_what_the_folder_holds(self, tmp_path: Path) -> None:
        """A mix with no room left is answerable: letting one go is what makes room for another."""
        rows = _rows_holding(1)
        coordinator = _stems_coordinator(
            mixes=True,
            folder_rows=rows,
            gathered_rows=_rows_holding(*[1] * MAX_STEM_SOURCES),
            room=0,
        )

        _add_folder(coordinator, _folder_of(tmp_path, 1))

        offered, room, _answer = coordinator._stem_selection_window.open.call_args.args
        assert offered == coordinator._converter_logic.gathered_rows + rows
        assert room == MAX_STEM_SOURCES

    def test_the_reading_is_put_on_screen(self, tmp_path: Path) -> None:
        """A folder of thousands takes seconds to read, so the reader is shown what they wait for."""
        coordinator = _stems_coordinator(mixes=False, folder_rows=_rows_holding(1))
        root = _folder_of(tmp_path, 1)

        _add_folder(coordinator, root)

        coordinator._scan_window.open.assert_called_once_with(root)

    def test_a_busy_application_leaves_the_folder_alone(self, tmp_path: Path) -> None:
        coordinator = _stems_coordinator(operation_active=True, folder_rows=_rows_holding(1))

        _add_folder(coordinator, _folder_of(tmp_path, 1))

        coordinator._converter_logic.gather_folder.assert_not_called()
        coordinator._stem_selection_window.open.assert_not_called()
