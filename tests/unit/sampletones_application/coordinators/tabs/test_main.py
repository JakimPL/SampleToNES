from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Final, Tuple
from unittest.mock import MagicMock, patch

import pytest

from sampletones_application.constants.conversion import MAX_STEM_SOURCES
from sampletones_application.constants.output import OutputKind
from sampletones_application.coordinators.tabs.hooks import MainTabHooks
from sampletones_application.coordinators.tabs.main import MainTabCoordinator
from sampletones_application.logic.main.converter.run import ConversionSuccess
from sampletones_application.logic.main.sources.scan import FolderScan
from sampletones_application.services.folder_scan.service import FolderScanService
from sampletones_application.tags.general import TAG_GLOBAL_DIALOG_EXIT_CONFIRMATION
from sampletones_application.tags.main import (
    TAG_MAIN_CONVERTER_DIALOG_CANCEL,
    TAG_MAIN_CONVERTER_DIALOG_CONVERSION_RUNNING,
    TAG_MAIN_CONVERTER_DIALOG_LOAD,
    TAG_MAIN_CONVERTER_DIALOG_OVERWRITE_TARGET,
)
from sampletones_core.constants.enums import ChannelName
from tests.suite.application import settled
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase
from tests.suite.files import LOCKED_FOLDER, held_at, requires_folder_permissions
from tests.suite.frames import held_frames
from tests.suite.language import FakeLanguageManager
from tests.suite.questions import StandingWindow, standing_window

__all__ = ["held_frames", "standing_window"]

CONVERSION_RUNNING_MESSAGE_KEY: Final[str] = "main.converter.message.conversion_running"
CONVERSION_RUNNING_TITLE_KEY: Final[str] = "main.converter.title.conversion_running_dialog"
LOAD_FILE_MESSAGE_KEY: Final[str] = "main.converter.message.load_file_prompt"
LOAD_BUTTON_KEY: Final[str] = "main.converter.label.load_button"
OPEN_BUTTON_KEY: Final[str] = "main.converter.label.open_button"
CLOSE_BUTTON_KEY: Final[str] = "main.converter.label.close_button"
STOP_BUTTON_KEY: Final[str] = "main.converter.label.stop_button"
CONTINUE_BUTTON_KEY: Final[str] = "main.converter.label.continue_button"
NOTHING_BELOW_KEY: Final[str] = "main.converter.message.scan_nothing_below"
EXIT_CONVERSION_MESSAGE_KEY: Final[str] = "global.dialog.message.exit_conversion_in_progress"
EXIT_LABEL_KEY: Final[str] = "global.dialog.label.exit"
MAIN_MODULE: Final[str] = "sampletones_application.coordinators.tabs.main"


def _hooks(*, operation_active: bool) -> MainTabHooks:
    """The tab's outward collaborator, every hook of which a test can read what reached it."""
    return MainTabHooks(
        is_operation_active=lambda: operation_active,
        on_busy_state_changed=MagicMock(),
        on_reconstruct_listed=MagicMock(),
        on_load_reconstruction=MagicMock(),
        on_load_library=MagicMock(),
        on_load_file=MagicMock(),
        on_load_directory=MagicMock(),
        on_canceled=MagicMock(),
        on_refresh_trees=MagicMock(),
        on_prepare_library=MagicMock(),
    )


def _coordinator(*, operation_active: bool, converting: bool = False) -> MainTabCoordinator:
    """A coordinator with only the state the doors to the list touch, bypassing the heavy
    constructor.

    ``converting`` is the converter's own run holding the list, and ``operation_active`` the busy
    authority, which a conversion and every other exclusive operation answer."""
    coordinator = MainTabCoordinator.__new__(MainTabCoordinator)
    coordinator._hooks = _hooks(operation_active=operation_active or converting)
    coordinator._dialogs = MagicMock()
    coordinator._language_manager = FakeLanguageManager()
    coordinator._session_manager = MagicMock()
    coordinator._converter_logic = MagicMock()
    coordinator._converter_logic.live = not converting
    coordinator._converter_logic.mixes = False
    coordinator._converter_logic.gathered_paths = ()
    coordinator._folder_scan = MagicMock()
    coordinator._scan_window = MagicMock()
    return coordinator


def _refused(coordinator: MainTabCoordinator) -> bool:
    """Whether the one notice saying the run holds the list was shown, and nothing else."""
    coordinator._dialogs.show_info.assert_called_once_with(
        TAG_MAIN_CONVERTER_DIALOG_CONVERSION_RUNNING,
        CONVERSION_RUNNING_MESSAGE_KEY,
        CONVERSION_RUNNING_TITLE_KEY,
    )
    return True


Door = Callable[[MainTabCoordinator, Path], None]
Reached = Callable[[MainTabCoordinator], bool]


def _menu_reconstruct_file(coordinator: MainTabCoordinator, path: Path) -> None:
    with patch(f"{MAIN_MODULE}.open_file_dialog", return_value=path):
        coordinator.reconstruct_file_dialog()


def _menu_reconstruct_directory(coordinator: MainTabCoordinator, path: Path) -> None:
    with patch(f"{MAIN_MODULE}.select_directory_dialog", return_value=path):
        coordinator.reconstruct_directory_dialog()


class TestEveryDoorToTheList(BaseTestSuite):
    """Every door that lists recordings meets one rule: the list refuses changes only while the
    converter's own run holds it, with one notice.

    Listing starts nothing, so a library generation, a render or an export leaves the list open,
    and the busy authority keeps Convert greyed until it ends. Ctrl-click and a double-click reach
    the same door Add as stem and Add folder do, since they gather too.
    """

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        door: Door
        reached: Reached

    test_cases = (
        TestCase(
            label="Reconstruct file... in the menu",
            door=_menu_reconstruct_file,
            reached=lambda coordinator: coordinator._hooks.on_reconstruct_listed.called,
        ),
        TestCase(
            label="Reconstruct folder... in the menu",
            door=_menu_reconstruct_directory,
            reached=lambda coordinator: coordinator._hooks.on_reconstruct_listed.called,
        ),
        TestCase(
            label="Reconstruct file in the browser",
            door=MainTabCoordinator.request_reconstruct_file,
            reached=lambda coordinator: coordinator._hooks.on_reconstruct_listed.called,
        ),
        TestCase(
            label="Reconstruct directory in the browser",
            door=MainTabCoordinator.request_reconstruct_directory,
            reached=lambda coordinator: coordinator._hooks.on_reconstruct_listed.called,
        ),
        TestCase(
            label="Add as stem, Ctrl-click or double-click on a recording",
            door=MainTabCoordinator._on_file_add_requested,
            reached=lambda coordinator: coordinator._converter_logic.gather_recordings.called,
        ),
        TestCase(
            label="Add folder or Ctrl-click on a folder",
            door=MainTabCoordinator._on_directory_add_requested,
            reached=lambda coordinator: coordinator._folder_scan.start.called,
        ),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda case: case.label)
    def test_a_run_holding_the_list_refuses_it_with_one_notice(self, test_case: TestCase) -> None:
        coordinator = _coordinator(operation_active=True, converting=True)

        test_case.door(coordinator, Path("/audio/take.wav"))

        assert (_refused(coordinator), test_case.reached(coordinator)) == (True, False)

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda case: case.label)
    def test_another_operation_leaves_the_list_open(self, test_case: TestCase) -> None:
        """A library generation holds the busy authority, and the list takes the recording all the same."""
        coordinator = _coordinator(operation_active=True)

        test_case.door(coordinator, Path("/audio/take.wav"))

        assert (test_case.reached(coordinator), coordinator._dialogs.show_info.called) == (True, False)

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda case: case.label)
    def test_each_attempt_shows_the_notice_again(self, test_case: TestCase) -> None:
        coordinator = _coordinator(operation_active=True, converting=True)

        test_case.door(coordinator, Path("/audio/take.wav"))
        test_case.door(coordinator, Path("/audio/take.wav"))

        assert coordinator._dialogs.show_info.call_count == 2


class TestAGestureLandingAfterARunStarted:
    """A gesture that lands later meets the rule again where it lands, since a run may have started in
    between: a folder read coming back, and a question answered."""

    def test_a_folder_read_for_add_folder_lists_nothing(self) -> None:
        coordinator = _coordinator(operation_active=True, converting=True)

        coordinator._gather_read(Path("/audio"), (Path("/audio/take.wav"),))

        assert (_refused(coordinator), coordinator._converter_logic.gather_folder.called) == (True, False)
        coordinator._scan_window.close.assert_called_once_with()

    def test_a_folder_read_for_a_reconstruct_lists_nothing(self) -> None:
        coordinator = _coordinator(operation_active=True, converting=True)

        coordinator._take_up_read(Path("/audio"), (Path("/audio/take.wav"),))

        assert (_refused(coordinator), coordinator._converter_logic.take_up_folder.called) == (True, False)
        coordinator._scan_window.close.assert_called_once_with()

    def test_replacing_the_mix_answered_after_a_run_started_lists_nothing(self) -> None:
        coordinator = _coordinator(operation_active=False)
        coordinator._converter_logic.mixes = True
        coordinator._converter_logic.gathered_paths = (Path("/audio/a.wav"),)
        coordinator.request_reconstruct_file(Path("/audio/b.wav"))
        coordinator._converter_logic.live = False

        coordinator._dialogs.show_confirmation.call_args.args[3]()

        assert (_refused(coordinator), coordinator._hooks.on_reconstruct_listed.called) == (True, False)

    def test_a_mix_picked_after_a_run_started_changes_nothing(self) -> None:
        coordinator = _stems_coordinator(mixes=True, folder_rows=_rows_holding(MAX_STEM_SOURCES, 1))
        coordinator._gather_read(Path("/audio"), tuple(Path(f"/audio/{index}.wav") for index in range(9)))
        coordinator._converter_logic.live = False
        _rows, _room, answer = coordinator._stem_selection_window.open.call_args.args

        answer((Path("/audio/0.wav"),))

        assert (_refused(coordinator), coordinator._converter_logic.mix_only.called) == (True, False)


class TestTheChannelKeys:
    """A channel key reaches the recording picked out on the terms the list's own keys keep."""

    @pytest.mark.parametrize("keys_active", [True, False], ids=["open", "put-away"])
    def test_a_key_reaches_the_pick_only_while_the_list_answers_keys(self, keys_active: bool) -> None:
        coordinator = _coordinator(operation_active=False)
        coordinator._converter_panel = MagicMock(keys_active=keys_active)

        coordinator.toggle_channel(ChannelName.TRIANGLE)

        assert coordinator._converter_logic.toggle_channel.called is keys_active


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
    """Canceling is destructive, so the panel's cancel intent asks for confirmation before the
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
SCAN_FAILED_KEY: Final[str] = "main.converter.message.scan_failed"
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
    coordinator._dialogs = MagicMock()
    coordinator._language_manager = FakeLanguageManager()
    coordinator._session_manager = MagicMock()
    coordinator._converter_logic = MagicMock()
    coordinator._converter_logic.live = True
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
    coordinator._folder_scan = FolderScan(FolderScanService(priority=coordinator._repaint_priority))
    coordinator._folder_scan.on_started = coordinator._scan_window.open
    coordinator._folder_scan.on_progress = coordinator._scan_window.report
    coordinator._folder_scan.on_stopped = coordinator._scan_window.close
    coordinator._folder_scan.on_failed = coordinator._on_scan_failed
    return coordinator


def _folder_of(tmp_path: Path, count: int) -> Path:
    """A folder holding that many recordings, which the reading below it finds."""
    root = tmp_path / "takes"
    root.mkdir(exist_ok=True)
    for index in range(count):
        (root / f"take_{index:02d}.wav").touch()

    return root


def _add_folder(coordinator: MainTabCoordinator, root: Path) -> None:
    """Asks for the folder and waits for the reading, the way a reader does.

    The walk's reports reach the coordinator through the queue the render loop drains, so the case
    drains it once the walk has ended.
    """
    settled(lambda: coordinator._on_directory_add_requested(root))


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
        answer([gathered[0]])
        coordinator._converter_logic.mix_only.assert_called_once_with([gathered[0]])

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

    def test_a_folder_holding_no_recordings_says_so(self, tmp_path: Path) -> None:
        """The reading is what knows what a folder holds, so the answer arrives when it comes back
        and the setup stands as it was."""
        coordinator = _stems_coordinator(mixes=False)
        root = _folder_of(tmp_path, 0)

        _add_folder(coordinator, root)

        coordinator._converter_logic.gather_folder.assert_not_called()
        assert coordinator._dialogs.show_info.call_args.args[1] == NOTHING_BELOW_KEY

    @requires_folder_permissions
    def test_a_folder_it_may_not_open_says_so_and_adds_nothing(self, tmp_path: Path) -> None:
        coordinator = _stems_coordinator(mixes=False)
        root = _folder_of(tmp_path, 2)

        with held_at(root, LOCKED_FOLDER):
            _add_folder(coordinator, root)

        coordinator._converter_logic.gather_folder.assert_not_called()
        failure, message = coordinator._dialogs.show_error.call_args.args
        assert isinstance(failure, PermissionError)
        assert message == SCAN_FAILED_KEY


class TestFileAdd:
    """A recording added from the browser's menu joins the setup, whichever run it names."""

    def test_a_recording_joins_the_list(self, tmp_path: Path) -> None:
        recording = tmp_path / "bass.wav"
        recording.touch()
        coordinator = _stems_coordinator()

        coordinator._on_file_add_requested(recording)

        coordinator._converter_logic.gather_recordings.assert_called_once_with([recording])


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


class TestReconstructListsWhatItNames:
    """A Reconstruct lists what it names to convert one apiece, asking first only about a mix it replaces."""

    def _coordinator(self, *, mixes: bool, gathered: Tuple[Path, ...] = ()) -> MainTabCoordinator:
        coordinator = _stems_coordinator(mixes=mixes, gathered=gathered)
        coordinator._folder_scan = MagicMock()
        return coordinator

    @pytest.mark.parametrize("gathered", [(), (Path("/audio/a.wav"),)])
    def test_a_list_writing_one_apiece_takes_it_straight_away(self, tmp_path: Path, gathered: Tuple[Path, ...]) -> None:
        coordinator = self._coordinator(mixes=False, gathered=gathered)

        coordinator.request_reconstruct_file(tmp_path / "a.wav")

        coordinator._converter_logic.take_up_recording.assert_called_once_with(tmp_path / "a.wav")
        coordinator._hooks.on_reconstruct_listed.assert_called_once_with()
        coordinator._dialogs.show_confirmation.assert_not_called()

    def test_a_recording_listed_leaves_its_folder_for_the_next_reconstruct_dialog(self, tmp_path: Path) -> None:
        coordinator = self._coordinator(mixes=False)

        coordinator.request_reconstruct_file(tmp_path / "a.wav")

        coordinator._session_manager.set_audio_input_path.assert_called_once_with(tmp_path)

    def test_a_folder_listed_is_left_for_the_next_reconstruct_dialog(self, tmp_path: Path) -> None:
        coordinator = self._coordinator(mixes=False)

        coordinator.request_reconstruct_directory(tmp_path)

        coordinator._session_manager.set_audio_input_path.assert_called_once_with(tmp_path)

    def test_an_empty_mix_gives_way_straight_away(self, tmp_path: Path) -> None:
        coordinator = self._coordinator(mixes=True)

        coordinator.request_reconstruct_directory(tmp_path)

        coordinator._folder_scan.start.assert_called_once_with(tmp_path, coordinator._take_up_read)
        coordinator._hooks.on_reconstruct_listed.assert_called_once_with()
        coordinator._dialogs.show_confirmation.assert_not_called()

    def test_a_mix_holding_recordings_is_asked_about_first(self, tmp_path: Path) -> None:
        coordinator = self._coordinator(mixes=True, gathered=(Path("/audio/a.wav"),))

        coordinator.request_reconstruct_file(tmp_path / "b.wav")
        coordinator.request_reconstruct_directory(tmp_path)

        coordinator._hooks.on_reconstruct_listed.assert_not_called()
        prompts = [call.args[1] for call in coordinator._dialogs.show_confirmation.call_args_list]
        assert prompts == [DISCARD_STEMS_PROMPT_KEY, DISCARD_STEMS_PROMPT_KEY]

    def test_confirming_lists_what_was_named(self, tmp_path: Path) -> None:
        coordinator = self._coordinator(mixes=True, gathered=(Path("/audio/a.wav"),))

        coordinator.request_reconstruct_directory(tmp_path)
        coordinator._dialogs.show_confirmation.call_args.args[3]()

        coordinator._folder_scan.start.assert_called_once_with(tmp_path, coordinator._take_up_read)

    def test_declining_keeps_the_mix(self, tmp_path: Path) -> None:
        coordinator = self._coordinator(mixes=True, gathered=(Path("/audio/a.wav"),))

        coordinator.request_reconstruct_directory(tmp_path)
        coordinator._dialogs.show_confirmation.call_args.kwargs["on_cancel"]()

        coordinator._converter_logic.set_output.assert_not_called()
        coordinator._hooks.on_reconstruct_listed.assert_not_called()


class TestTakingUpWhatAReconstructNamed:
    """A recording is listed at once; a folder is read first and listed once the reading is done."""

    def test_a_recording_is_listed(self, tmp_path: Path) -> None:
        coordinator = _stems_coordinator(mixes=False)

        coordinator._take_up_path(tmp_path / "take.wav")

        coordinator._converter_logic.take_up_recording.assert_called_once_with(tmp_path / "take.wav")
        coordinator._converter_logic.start_conversion.assert_not_called()

    def test_a_folder_is_listed_with_what_it_holds(self, tmp_path: Path) -> None:
        coordinator = _stems_coordinator(mixes=False)
        root = _folder_of(tmp_path, 2)

        settled(lambda: coordinator._take_up_path(root))

        listed, found = coordinator._converter_logic.take_up_folder.call_args.args
        assert listed == root
        assert {path.name for path in found} == {"take_00.wav", "take_01.wav"}
        coordinator._converter_logic.start_conversion.assert_not_called()

    def test_a_folder_holding_no_recordings_says_so(self, tmp_path: Path) -> None:
        coordinator = _stems_coordinator(mixes=False)
        root = _folder_of(tmp_path, 0)

        settled(lambda: coordinator._take_up_path(root))

        coordinator._converter_logic.take_up_folder.assert_not_called()
        assert coordinator._dialogs.show_info.call_args.args[1] == NOTHING_BELOW_KEY


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
        answer([Path("/audio/take.wav")])
        coordinator._converter_logic.mix_only.assert_called_once_with([Path("/audio/take.wav")])

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


class TestTheExitAsksAboutARunningConversion:
    """Exiting stops a running conversion, so the reader is asked first."""

    def _coordinator(self, *, active: bool) -> MainTabCoordinator:
        coordinator = _coordinator(operation_active=False)
        coordinator._converter_logic.is_active = active
        return coordinator

    def test_an_idle_converter_lets_the_exit_go_on(self) -> None:
        coordinator = self._coordinator(active=False)
        proceed = MagicMock()
        decline = MagicMock()

        coordinator.guard_exit(proceed, decline)

        proceed.assert_called_once_with()
        decline.assert_not_called()
        coordinator._dialogs.show_confirmation.assert_not_called()

    def test_a_question_waits_while_another_window_stands(self, standing_window: StandingWindow) -> None:
        coordinator = self._coordinator(active=True)

        coordinator.guard_exit(MagicMock(), MagicMock())

        coordinator._dialogs.show_confirmation.assert_not_called()
        standing_window.leave()
        coordinator._dialogs.show_confirmation.assert_called_once()

    def test_a_conversion_ending_meanwhile_lets_the_exit_go_on(self, standing_window: StandingWindow) -> None:
        coordinator = self._coordinator(active=True)
        proceed = MagicMock()
        coordinator.guard_exit(proceed, MagicMock())

        coordinator._converter_logic.is_active = False
        standing_window.leave()

        proceed.assert_called_once_with()
        coordinator._dialogs.show_confirmation.assert_not_called()

    def test_a_running_conversion_asks_first(self) -> None:
        coordinator = self._coordinator(active=True)
        proceed = MagicMock()
        decline = MagicMock()

        coordinator.guard_exit(proceed, decline)

        proceed.assert_not_called()
        decline.assert_not_called()
        args, kwargs = coordinator._dialogs.show_confirmation.call_args
        assert args[0] == TAG_GLOBAL_DIALOG_EXIT_CONFIRMATION
        assert args[1] == EXIT_CONVERSION_MESSAGE_KEY
        assert args[3] is proceed
        assert kwargs["ok_label"] == EXIT_LABEL_KEY
        assert kwargs["on_cancel"] is decline
