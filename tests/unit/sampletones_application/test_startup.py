from contextlib import ExitStack, contextmanager
from pathlib import Path
from typing import Any, Callable, Dict, Final, FrozenSet, Generator, List, Tuple, Union
from unittest.mock import PropertyMock, patch

import dearpygui.dearpygui as dpg
import pytest

from sampletones_application.application import Application
from sampletones_application.categories.hierarchy import Tab
from sampletones_application.config.managers.session import SessionManager
from sampletones_application.config.profile import UserProfile
from sampletones_application.constants.conversion import MAX_STEM_SOURCES
from sampletones_application.constants.keybindings import DEFAULT_SCHEME_NAME
from sampletones_application.constants.output import OutputKind
from sampletones_application.constants.sources import SettingsField, SourceKind
from sampletones_application.logic.history.action import HistoryAction
from sampletones_application.tags.compose import compose_tag
from sampletones_application.tags.general import (
    SUF_BUTTON,
    SUF_GROUP,
    SUF_STRIP,
    SUF_TABLE,
    SUF_TABLE_COLUMN,
    SUF_TEXT,
    TAG_GLOBAL_THEME_STEMS_ROW_INERT,
)
from sampletones_application.tags.main import (
    PRE_MAIN_CONVERTER_CANDIDATE,
    PRE_MAIN_SOURCE_SLOT,
    TAG_MAIN_ADVANCED_PANEL,
    TAG_MAIN_ADVANCED_PANEL_ADVANCED_CELL,
    TAG_MAIN_CONFIG_PANEL,
    TAG_MAIN_CONFIG_PANEL_CONFIG_CELL,
    TAG_MAIN_CONFIG_TABLE_CONFIG_ROW,
    TAG_MAIN_CONVERTER_GROUP_CONTROLS,
    TAG_MAIN_CONVERTER_GROUP_ORDER,
    TAG_MAIN_CONVERTER_PANEL,
    TAG_MAIN_CONVERTER_RADIO_MODE,
    TAG_MAIN_CONVERTER_TOOLTIP_HIERARCHY_MODE,
    TAG_MAIN_CONVERTER_WINDOW_STEMS,
    TAG_MAIN_SOURCE_GROUP_GRID,
    TAG_MAIN_SOURCE_PANEL,
    TAG_MAIN_SOURCE_TEXT_INSPECTING,
    TAG_MAIN_SOURCE_TEXT_UNPICKED,
)
from sampletones_application.ui.elements.stems.list import GUIStemsList
from sampletones_application.ui.elements.stems.tags import StemsTags
from sampletones_application.ui.panels.main import explorer as explorer_module
from sampletones_application.utils.gui.keyboard.event import KeyEvent
from sampletones_application.utils.gui.keyboard.modifiers import Modifier
from sampletones_application.utils.gui.shortcuts.ids import (
    CHANNEL_SHORTCUT_IDS,
    TAB_SHORTCUT_IDS,
    ShortcutId,
)
from sampletones_application.utils.parallelization.background import (
    stop_background_workers,
)
from sampletones_application.utils.parallelization.thread import SingleThreadExecutor
from sampletones_application.view_model.main.converter import ConversionPhase, ConverterViewModel
from sampletones_application.view_model.shared.stems import StemRowViewModel
from sampletones_core.constants.enums import ChannelName
from sampletones_core.reconstructions import Reconstruction
from sampletones_core.reconstructions.converter.paths import get_audio_files
from sampletones_core.structures.tree import FileSystemNode, NodeType

REBOUND_UNDO: Final[Dict[str, str]] = {"Undo": "Ctrl+Alt+U"}
DRAG_PAYLOAD_SLOT: Final[int] = 3
UNBUILT_ROW: Final[str] = "browser.row.unbuilt"

_DPG_DISPLAY_FUNCTIONS = [
    "create_context",
    "create_viewport",
    "setup_dearpygui",
    "show_viewport",
    "render_dearpygui_frame",
    "set_viewport_clear_color",
    "set_viewport_pos",
    "set_viewport_width",
    "set_viewport_height",
    "set_viewport_title",
    "set_viewport_decorated",
    "set_viewport_resize_callback",
    "toggle_viewport_fullscreen",
    "set_exit_callback",
    "set_primary_window",
]

_VIEWPORT_CLIENT_WIDTH: Final[int] = 1280
_VIEWPORT_CLIENT_HEIGHT: Final[int] = 720


def _display_patches() -> List[Any]:
    display_patches = [patch(f"dearpygui.dearpygui.{name}", return_value=None) for name in _DPG_DISPLAY_FUNCTIONS]
    display_patches.append(
        patch(
            "dearpygui.dearpygui.get_viewport_client_width",
            return_value=_VIEWPORT_CLIENT_WIDTH,
        )
    )
    display_patches.append(
        patch(
            "dearpygui.dearpygui.get_viewport_client_height",
            return_value=_VIEWPORT_CLIENT_HEIGHT,
        )
    )
    display_patches.append(patch("sampletones_application.utils.callbacks.queue.CallbackQueue.start"))
    return display_patches


@contextmanager
def _no_audio_devices() -> Generator[None, None, None]:
    """The machine a headless run comes up on: the backend reports no output device at all."""
    with (
        patch("pyaudio.PyAudio.get_device_count", return_value=0),
        patch(
            "pyaudio.PyAudio.get_default_output_device_info",
            side_effect=OSError,
        ),
    ):
        yield


def _profile(directory: Path) -> UserProfile:
    """Starts the application on a profile of its own, in the state a first run finds.

    The settings and the keys an application comes up on are read from its profile, so a suite
    given the user's own answers for whatever that machine prefers. A directory per test is what
    holds a run to the shipped defaults.
    """
    return UserProfile(
        config=directory / "config.yaml",
        state=directory / "state.yaml",
    )


class TestGUIStartup:
    @pytest.fixture(autouse=True)
    def dpg_context(self) -> Generator[Any, Application, Any]:
        dpg.create_context()
        yield
        stop_background_workers()
        SingleThreadExecutor.reset_shutdown()
        dpg.destroy_context()

    def test_initializes_without_error(self, tmp_path: Path) -> None:
        with ExitStack() as stack:
            for display_patch in _display_patches():
                stack.enter_context(display_patch)

            Application(profile=_profile(tmp_path))

    def test_initializes_where_nothing_can_play(self, tmp_path: Path) -> None:
        """Editing a song, exporting a module and rendering to a file need no output device.

        The rate the audio is rendered at is the consumer's to state, so a machine offering no
        device to play through still opens the window and everything that writes rather than
        sounds works on it.
        """
        with ExitStack() as stack:
            for display_patch in _display_patches():
                stack.enter_context(display_patch)
            stack.enter_context(_no_audio_devices())

            Application(profile=_profile(tmp_path))


@pytest.fixture
def app(tmp_path: Path) -> Generator[Any, Application, Any]:
    dpg.create_context()
    try:
        with ExitStack() as stack:
            for display_patch in _display_patches():
                stack.enter_context(display_patch)

            yield Application(profile=_profile(tmp_path))
    finally:
        stop_background_workers()
        SingleThreadExecutor.reset_shutdown()
        dpg.destroy_context()


class TestKeybindingPreferences:
    """The application runs on the keys the session stores, which is what makes a rebind stick.

    The session names the scheme it runs under, so a case reads the same keys on whichever platform
    the suite runs; a Mac opens a fresh profile on Command.
    """

    @pytest.fixture
    def application(self, tmp_path: Path) -> Generator[Any, Application, Any]:
        dpg.create_context()
        try:
            with ExitStack() as stack:
                for display_patch in _display_patches():
                    stack.enter_context(display_patch)

                stack.enter_context(
                    patch.object(
                        SessionManager,
                        "shortcut_scheme_name",
                        new_callable=PropertyMock,
                        return_value=DEFAULT_SCHEME_NAME,
                    )
                )
                stack.enter_context(
                    patch.object(
                        SessionManager,
                        "shortcut_overrides",
                        new_callable=PropertyMock,
                        return_value=REBOUND_UNDO,
                    )
                )
                yield Application(profile=_profile(tmp_path))
        finally:
            stop_background_workers()
            SingleThreadExecutor.reset_shutdown()
            dpg.destroy_context()

    def test_a_stored_override_reaches_the_keys_in_place(self, application: Application) -> None:
        assert application._shortcut_source.display(ShortcutId.UNDO) == REBOUND_UNDO["Undo"]

    def test_the_actions_the_override_leaves_alone_keep_the_scheme_s_keys(
        self,
        application: Application,
    ) -> None:
        assert application._shortcut_source.display(ShortcutId.SAVE_PROJECT) == "Ctrl+S"

    def test_another_scheme_hands_its_keys_to_the_dispatcher(self, application: Application) -> None:
        """A rebind reaches what has already read a combination, which is how it takes effect live."""
        with patch.object(application.shortcut_manager, "rebind") as rebind:
            application._shortcut_source.activate(application._shortcut_catalog.default)

        rebind.assert_called_once()


class TestStartupRestoreDelegation:
    """Application only forwards the startup restore to the domain coordinators, which
    are the recovery boundary (docs/development/architecture.md § Error Handling Policy). The
    recovery behavior itself is covered by the coordinator tests.
    """

    def test_project_restore_delegates_to_coordinator(self, app: Application) -> None:
        with patch.object(app._project_coordinator, "load_project_safely") as load_project_safely:
            app._try_load_project(Path("last.stp"))

        load_project_safely.assert_called_once_with(Path("last.stp"))

    def test_reconstruction_restore_delegates_to_coordinator(self, app: Application) -> None:
        with patch.object(app._reconstruction_coordinator, "load_reconstruction_safely") as load_reconstruction_safely:
            app._try_load_reconstruction(Path("last.stn"))

        load_reconstruction_safely.assert_called_once_with(Path("last.stn"))

    def test_library_load_delegates_to_coordinator(self, app: Application) -> None:
        with patch.object(app._instructions_tab, "load_library_safely") as load_library_safely:
            app._try_load_library(Path("last.ins"))

        load_library_safely.assert_called_once_with(Path("last.ins"))


class TestReconstructionSaveAsDetachment:
    """End-to-end proof that Save As severs a project sample from the open document.

    Exercises the fully wired application: an embedded reconstruction reports as owned and
    not saveable, and after Save As the open document becomes a standalone file-backed entity
    while the project's sample keeps its original reconstruction object.
    """

    def _embed_sample(
        self,
        app: Application,
        reconstruction_factory: Callable[[], Reconstruction],
    ) -> Any:
        app.project_controller.new()
        reconstruction = reconstruction_factory()
        with app.history.transaction(HistoryAction.ADD_SAMPLE):
            sample = app.project_controller.add_sample(reconstruction, "Lead")
        app._edit_project_voice(sample.id)
        return sample

    def test_embedded_reconstruction_is_owned_and_not_saveable(
        self,
        app: Application,
        reconstruction_factory: Callable[[], Reconstruction],
    ) -> None:
        sample = self._embed_sample(app, reconstruction_factory)

        assert app._owning_project_sample() is sample
        assert not app._reconstruction_coordinator.is_saveable()
        assert not app._build_menu_bar_viewmodel().reconstruction_saveable

    def test_embedded_reconstruction_needs_no_save_prompt_when_edited(
        self,
        app: Application,
        reconstruction_factory: Callable[[], Reconstruction],
    ) -> None:
        self._embed_sample(app, reconstruction_factory)
        app.reconstruction_manager.mark_updated()

        assert app._reconstruction_coordinator.is_unsaved()
        assert not app._reconstruction_coordinator._requires_save_confirmation()

    def test_save_as_detaches_open_document_from_the_project(
        self,
        app: Application,
        reconstruction_factory: Callable[[], Reconstruction],
        tmp_path: Path,
    ) -> None:
        sample = self._embed_sample(app, reconstruction_factory)
        original = sample.reconstruction

        app.reconstruction_manager.save_reconstruction_as(tmp_path / "lead.stn")

        assert app._owning_project_sample() is None
        assert app._reconstruction_coordinator.is_saveable()
        assert app._build_menu_bar_viewmodel().reconstruction_saveable
        assert app.reconstruction_manager.reconstruction is not original
        assert sample.reconstruction is original
        assert original in [sample.reconstruction for sample in app.project_manager.current.voices]


class TestAddOpenReconstructionToSequencer:
    """Adding the open standalone reconstruction to the sequencer embeds an independent copy.

    A project sample is self-contained, so its reconstruction is detached from its local
    source audio for portability. The reconstruction still open in the tab keeps its own
    source location and file backing, so its menu can still locate the original audio.
    """

    def _open_file_backed_reconstruction(
        self,
        app: Application,
        reconstruction_factory: Callable[[], Reconstruction],
        tmp_path: Path,
    ) -> Path:
        reconstruction_path = tmp_path / "lead.stn"
        reconstruction_factory().save(reconstruction_path)
        app.reconstruction_manager.load_reconstruction(reconstruction_path)
        return reconstruction_path

    def test_adding_open_document_keeps_its_source_audio(
        self,
        app: Application,
        reconstruction_factory: Callable[[], Reconstruction],
        tmp_path: Path,
    ) -> None:
        self._open_file_backed_reconstruction(app, reconstruction_factory, tmp_path)
        app.project_controller.new()
        source_before = app.reconstruction_manager.source_paths

        app._add_current_reconstruction_to_sequencer()

        assert source_before
        assert app.reconstruction_manager.source_paths == source_before
        assert app._build_menu_bar_viewmodel().locate_audio_enabled

    def test_embedded_sample_is_a_detached_copy(
        self,
        app: Application,
        reconstruction_factory: Callable[[], Reconstruction],
        tmp_path: Path,
    ) -> None:
        self._open_file_backed_reconstruction(app, reconstruction_factory, tmp_path)
        app.project_controller.new()

        app._add_current_reconstruction_to_sequencer()

        sample = app.project_manager.current.voices[0]
        assert sample.reconstruction is not app.reconstruction_manager.reconstruction
        assert sample.reconstruction.audio_filepath == ()
        assert not app._editing_project_sample()


def _press_shortcut(app: Application, shortcut_id: ShortcutId) -> None:
    """Routes the press the scheme in place gives an action, so a rebind carries the case with it."""
    combination = app._shortcut_source.shortcut(shortcut_id).combination
    assert combination is not None
    app.key_router.route(KeyEvent(key=combination.key, modifiers=combination.modifiers))


class TestChannelKeys:
    """One key per channel, reaching the switch of the tab in front of the reader.

    The whole application answers here, so a press travels the way it does at runtime: the router
    hands it to the dispatcher, the scheme names the action, and the tab on screen decides which
    of its controls the action reaches.
    """

    @staticmethod
    def _press(app: Application, channel: ChannelName, tab: Tab) -> None:
        with patch.object(app._shell, "get_current_tab", return_value=tab):
            _press_shortcut(app, CHANNEL_SHORTCUT_IDS[channel])

    @staticmethod
    def _gathered(app: Application, tmp_path: Path) -> List[Path]:
        paths = []
        for name in ["a.wav", "b.wav"]:
            path = tmp_path / name
            path.touch()
            paths.append(path)

        app._main_tab._converter_logic.gather_recordings(paths)
        return paths

    def test_the_main_tab_settles_the_channel_on_the_row_picked_out(
        self,
        app: Application,
        tmp_path: Path,
    ) -> None:
        """The key answers for the row the settings card is pointed at, which is the box beside it."""
        paths = self._gathered(app, tmp_path)
        app._main_tab._converter_logic.select_row(paths[0], SourceKind.RECORDING)
        held = ChannelName.TRIANGLE in _row_of(app, paths[0]).channels

        self._press(app, ChannelName.TRIANGLE, Tab.MAIN)

        assert (ChannelName.TRIANGLE in _row_of(app, paths[0]).channels) is not held

    def test_the_rows_it_was_not_pointed_at_stand_as_they_were(
        self,
        app: Application,
        tmp_path: Path,
    ) -> None:
        paths = self._gathered(app, tmp_path)
        app._main_tab._converter_logic.select_row(paths[0], SourceKind.RECORDING)
        held = ChannelName.TRIANGLE in _row_of(app, paths[1]).channels

        self._press(app, ChannelName.TRIANGLE, Tab.MAIN)

        assert (ChannelName.TRIANGLE in _row_of(app, paths[1]).channels) is held

    def test_the_main_tab_holding_nothing_picked_out_leaves_the_list_alone(
        self,
        app: Application,
        tmp_path: Path,
    ) -> None:
        paths = self._gathered(app, tmp_path)
        standing = [_row_of(app, path).channels for path in paths]

        self._press(app, ChannelName.TRIANGLE, Tab.MAIN)

        assert [_row_of(app, path).channels for path in paths] == standing

    def test_the_sequencer_switches_its_mix(self, app: Application) -> None:
        self._press(app, ChannelName.NOISE, Tab.SEQUENCER)

        assert app._sequencer_tab.channels.is_muted(ChannelName.NOISE)

    def test_a_second_press_returns_the_mix_it_started_from(self, app: Application) -> None:
        self._press(app, ChannelName.PULSE1, Tab.SEQUENCER)
        self._press(app, ChannelName.PULSE1, Tab.SEQUENCER)

        assert not app._sequencer_tab.channels.any_muted

    def test_the_reconstructions_tab_holding_nothing_leaves_the_mix_alone(self, app: Application) -> None:
        """With no reconstruction loaded every slice reads as unavailable, so the key rests there."""
        self._press(app, ChannelName.PULSE2, Tab.RECONSTRUCTIONS)

        assert not app._sequencer_tab.channels.any_muted

    def test_the_main_tab_leaves_the_sequencer_mix_alone(self, app: Application) -> None:
        self._press(app, ChannelName.PULSE1, Tab.MAIN)

        assert not app._sequencer_tab.channels.any_muted


class TestTabKeys:
    """One key per tab, bringing it to the front from wherever the reader stands.

    The whole application answers here, so a press travels the way it does at runtime: the router
    hands it to the dispatcher, the scheme names the action, and the shell puts the tab on screen.
    """

    @pytest.mark.parametrize("tab", tuple(TAB_SHORTCUT_IDS), ids=lambda tab: str(tab))
    def test_the_key_puts_its_tab_on_screen(self, app: Application, tab: Tab) -> None:
        with patch.object(app._shell, "set_current_tab") as set_current_tab:
            _press_shortcut(app, TAB_SHORTCUT_IDS[tab])

        set_current_tab.assert_called_once_with(tab)

    @pytest.mark.parametrize("tab", tuple(TAB_SHORTCUT_IDS), ids=lambda tab: str(tab))
    def test_the_key_answers_while_a_field_is_edited(self, app: Application, tab: Tab) -> None:
        """Naming a tab reaches it the way stepping to the next one does, typing included."""
        assert app._shortcut_source.shortcut(TAB_SHORTCUT_IDS[tab]).field_transparent


def stems_list(app: Application) -> GUIStemsList:
    """The converter card's stems list, which owns the tags its rows carry."""
    return app._main_tab._converter_panel.stems_list


def drop(tag: str, payload: str) -> None:
    """Deliver ``payload`` to whatever ``tag`` accepts drops with, the way DearPyGui would."""
    dpg.get_item_configuration(tag)["drop_callback"](dpg.get_alias_id(tag), payload)


def _click_row(app: Application, path: Path) -> None:
    """Clicks a row the way DearPyGui reports a selectable being picked."""
    name_tag = stems_list(app).tags.row(str(path), SUF_TEXT)
    dpg.get_item_callback(name_tag)(name_tag, True, str(path))


def _click_slot_box(field: SettingsField, channel_name: ChannelName) -> None:
    """Clicks one of the settings card's boxes, the way DearPyGui reports a checkbox."""
    box = compose_tag(PRE_MAIN_SOURCE_SLOT, field.value, channel_name.value)
    dpg.get_item_callback(box)(box, True, dpg.get_item_user_data(box))


def _row_of(app: Application, path: Path) -> StemRowViewModel:
    """The row the converter last drew for ``path``."""
    row = stems_list(app).row(str(path))
    assert row is not None
    return row


def _level_of(app: Application, path: Path) -> str:
    """The level band the row for ``path`` is drawn in."""
    return str(dpg.get_item_parent(stems_list(app).tags.row(str(path), SUF_GROUP)))


def _reports_running(app: Application, status_text: str, progress: float) -> None:
    """Puts the panel in front of a conversion under way, the way the converter reports one."""
    converter_logic = app._main_tab._converter_logic
    emitted: List[ConverterViewModel] = []
    listener = converter_logic.on_view_changed
    converter_logic.on_view_changed = emitted.append
    converter_logic.emit_initial_view()
    converter_logic.on_view_changed = listener

    running = emitted[0].model_copy(
        update={"phase": ConversionPhase.RUNNING, "status_text": status_text, "progress": progress}
    )
    app._main_tab._on_converter_view_changed(running)


def _ctrl_click_folder(app: Application, directory: Path) -> None:
    """Reports a Ctrl-click on a folder's row, the way the browser does."""
    panel = app._main_tab._explorer_panel
    node = FileSystemNode(directory.name, node_type=NodeType.DIRECTORY, filepath=directory)
    with patch.object(explorer_module, "capture_modifiers", return_value=frozenset({Modifier.CTRL})):
        panel._directory_node_clicked(node, UNBUILT_ROW)


DOUBLE_CLICKED_HANDLER = 1


def _double_click_name(prefix: str, key: str) -> None:
    """Double-click one row's name in a stems list, the way DearPyGui reports the gesture."""
    tags = StemsTags(prefix=prefix)
    handler = dpg.get_item_children(tags.handlers(SUF_TEXT), 1)[DOUBLE_CLICKED_HANDLER]
    name_tag = tags.row(key, SUF_TEXT)
    dpg.get_item_callback(handler)(name_tag, (dpg.mvMouseButton_Left, dpg.get_alias_id(name_tag)))


class TestGatheringAFolderIntoAMix:
    """A folder bringing in more than a mix holds is a question, and the answer reaches the mix.

    The question names the recordings to gather, so what the reader picks is what the setup takes
    up — the whole chain from the browser gesture to the rows the card ends up drawing.
    """

    @staticmethod
    def _folder(tmp_path: Path, count: int) -> Path:
        directory = tmp_path / "takes"
        directory.mkdir()
        for index in range(count):
            (directory / f"take_{index:02d}.wav").touch()

        return directory

    @staticmethod
    def _ask(app: Application, directory: Path) -> None:
        """Ctrl-clicks the folder and waits for the reading, the way a reader does."""
        _ctrl_click_folder(app, directory)
        SingleThreadExecutor.join_all()

    def test_it_asks_rather_than_gathers(self, app: Application, tmp_path: Path) -> None:
        directory = self._folder(tmp_path, MAX_STEM_SOURCES + 3)
        app._main_tab._converter_logic.set_output(OutputKind.MIXED)

        with patch.object(app._main_tab._stem_selection_window, "open") as opened:
            self._ask(app, directory)

        opened.assert_called_once()
        assert app._main_tab._converter_logic.gathered_paths == ()

    def test_what_the_reader_picks_is_what_the_mix_takes(self, app: Application, tmp_path: Path) -> None:
        directory = self._folder(tmp_path, MAX_STEM_SOURCES + 3)
        app._main_tab._converter_logic.set_output(OutputKind.MIXED)
        with patch.object(app._main_tab._stem_selection_window, "open") as opened:
            self._ask(app, directory)

        offered, _room, answer = opened.call_args.args
        picked = [row.path for row in offered[:MAX_STEM_SOURCES]]
        answer(picked)

        assert set(app._main_tab._converter_logic.gathered_paths) == set(picked)

    def test_the_switch_reads_the_output_the_setup_holds(self, app: Application, tmp_path: Path) -> None:
        """A question about a mix leaves the run as it is until the reader answers it."""
        converter_logic = app._main_tab._converter_logic
        paths = []
        for index in range(MAX_STEM_SOURCES + 2):
            path = tmp_path / f"take_{index:02d}.wav"
            path.touch()
            paths.append(path)

        converter_logic.gather_recordings(paths)
        standing = dpg.get_value(TAG_MAIN_CONVERTER_RADIO_MODE)

        with patch.object(app._main_tab._stem_selection_window, "open"):
            app._main_tab._request_output(OutputKind.MIXED)

        assert dpg.get_value(TAG_MAIN_CONVERTER_RADIO_MODE) == standing

    def test_a_folder_the_mix_still_holds_is_gathered(self, app: Application, tmp_path: Path) -> None:
        directory = self._folder(tmp_path, MAX_STEM_SOURCES - 1)
        app._main_tab._converter_logic.set_output(OutputKind.MIXED)

        with patch.object(app._main_tab._stem_selection_window, "open") as opened:
            self._ask(app, directory)

        opened.assert_not_called()
        assert len(app._main_tab._converter_logic.gathered_paths) == MAX_STEM_SOURCES - 1

    def test_a_recording_in_the_question_sounds_where_the_reader_asks_for_it(
        self,
        app: Application,
        tmp_path: Path,
    ) -> None:
        """A reader decides by ear, so a double-click in the question reaches the player the
        converter's list reaches, the whole way from the gesture to the device."""
        directory = self._folder(tmp_path, MAX_STEM_SOURCES + 3)
        app._main_tab._converter_logic.set_output(OutputKind.MIXED)
        with patch.object(app._main_tab._stem_selection_window, "open") as opened:
            self._ask(app, directory)

        offered, room, answer = opened.call_args.args
        window = app._main_tab._stem_selection_window
        window.open(offered, room, answer)
        recording = offered[0]

        with patch.object(app.audio_device_manager, "play_file") as sounded:
            _double_click_name(PRE_MAIN_CONVERTER_CANDIDATE, recording.key)

        assert sounded.call_args.args[0] == recording.path


class TestMainTabReadingOrder:
    """The tab reads in one direction: what a run is set up with, what it gathers, what a row takes.

    The reconstruction card names whichever row the converter's list stands on, so it follows the
    list it reads rather than standing above it.
    """

    @staticmethod
    def _identity(item: Union[int, str]) -> int:
        """One reading of an item, since DearPyGui answers with an alias where a tag names one."""
        return dpg.get_alias_id(item) if isinstance(item, str) else item

    @classmethod
    def _place(cls, tag: str) -> Tuple[int, int]:
        """Where a card stands: the parent holding it, and its place among that parent's children."""
        item = cls._identity(tag)
        parent = cls._identity(dpg.get_item_parent(item))
        children = [cls._identity(child) for child in dpg.get_item_children(parent)[1]]
        return parent, children.index(item)

    @classmethod
    def _stands_within(cls, tag: str, ancestor: str) -> bool:
        item = cls._identity(tag)
        wanted = cls._identity(ancestor)
        while item:
            if item == wanted:
                return True
            item = cls._identity(dpg.get_item_parent(item))

        return False

    def test_the_reconstruction_card_follows_the_converter(self, app: Application) -> None:
        converter_parent, converter_place = self._place(TAG_MAIN_CONVERTER_PANEL)
        card_parent, card_place = self._place(TAG_MAIN_SOURCE_PANEL)

        assert card_parent == converter_parent
        assert card_place > converter_place

    def test_the_settings_cards_share_the_row_above(self, app: Application) -> None:
        assert self._stands_within(TAG_MAIN_CONFIG_PANEL, TAG_MAIN_CONFIG_TABLE_CONFIG_ROW)
        assert self._stands_within(TAG_MAIN_ADVANCED_PANEL, TAG_MAIN_CONFIG_TABLE_CONFIG_ROW)

    def test_the_row_holds_its_height_until_both_cards_collapse(self, app: Application) -> None:
        """The row is the two settings cards' own, so it is theirs to give up."""
        coordinator = app._main_tab
        with (
            patch.object(type(coordinator._config_panel), "collapsed", PropertyMock(return_value=True)),
            patch.object(type(coordinator._advanced_settings_panel), "collapsed", PropertyMock(return_value=True)),
        ):
            coordinator._sync_config_row_height()

        assert dpg.get_item_configuration(TAG_MAIN_CONFIG_TABLE_CONFIG_ROW)["height"] == 0

    @staticmethod
    def _share(cell_tag: str) -> float:
        """The share of the settings row the column behind a cell holds."""
        column = compose_tag(cell_tag, SUF_TABLE_COLUMN)
        return float(dpg.get_item_configuration(column)["init_width_or_weight"])

    def test_the_advanced_card_leaves_the_row_and_comes_back_to_its_half(self, app: Application) -> None:
        """One toggle leaves the row to the general card, the other gives the advanced one its half.

        Which way the first toggle goes is whatever the session was left at, so the pair of shares
        is what the rule states: nothing while the card is put away, and the general card's own
        share once it stands again.
        """
        coordinator = app._main_tab
        general = self._share(TAG_MAIN_CONFIG_PANEL_CONFIG_CELL)

        coordinator.toggle_advanced_settings()
        first = self._share(TAG_MAIN_ADVANCED_PANEL_ADVANCED_CELL)
        coordinator.toggle_advanced_settings()
        second = self._share(TAG_MAIN_ADVANCED_PANEL_ADVANCED_CELL)

        assert general > 0
        assert {first, second} == {0.0, general}


class TestBrowserGathering:
    """What a gesture in the browser gathers: a plain click walks it, and gathering is asked for.

    Reading every recording below a folder is work a reader asks for, so it answers the gathering
    gesture alone. A plain click walks the browser and leaves the conversion as it is — opening a
    folder, playing a recording — which is what keeps navigating a large tree from gathering it.
    Ctrl brings in whatever the row names, and a double-click brings in a recording.
    """

    @staticmethod
    def _folder(directory: Path) -> FileSystemNode:
        return FileSystemNode(directory.name, node_type=NodeType.DIRECTORY, filepath=directory)

    @staticmethod
    def _tree(tmp_path: Path) -> Path:
        directory = tmp_path / "takes"
        directory.mkdir()
        (directory / "one.wav").touch()
        (directory / "deeper").mkdir()
        (directory / "deeper" / "two.wav").touch()
        return directory

    def _click(self, app: Application, directory: Path, *, modifiers: FrozenSet[Modifier]) -> None:
        """Clicks a folder's row, with whatever the reader was holding down, and lets it settle."""
        panel = app._main_tab._explorer_panel
        with patch.object(explorer_module, "capture_modifiers", return_value=modifiers):
            panel._directory_node_clicked(self._folder(directory), UNBUILT_ROW)

        SingleThreadExecutor.join_all()

    def test_a_plain_click_gathers_nothing(self, app: Application, tmp_path: Path) -> None:
        directory = self._tree(tmp_path)

        self._click(app, directory, modifiers=frozenset())

        assert app._main_tab._converter_logic.gathered_paths == ()

    def test_ctrl_gathers_the_whole_tree_below_it(self, app: Application, tmp_path: Path) -> None:
        directory = self._tree(tmp_path)

        self._click(app, directory, modifiers=frozenset({Modifier.CTRL}))

        assert set(app._main_tab._converter_logic.gathered_paths) == {
            directory / "one.wav",
            directory / "deeper" / "two.wav",
        }

    def test_a_plain_click_on_a_recording_gathers_nothing(self, app: Application, tmp_path: Path) -> None:
        """A plain click previews a recording, so listening through a folder leaves the run alone."""
        recording = self._recording(tmp_path)
        panel = app._main_tab._explorer_panel

        with patch.object(explorer_module, "capture_modifiers", return_value=frozenset()):
            panel._audio_node_clicked(self._node(recording))

        assert app._main_tab._converter_logic.gathered_paths == ()

    def test_a_double_click_on_a_recording_gathers_it(self, app: Application, tmp_path: Path) -> None:
        """A recording is one path, so naming it costs nothing and one gesture brings it in."""
        recording = self._recording(tmp_path)
        panel = app._main_tab._explorer_panel

        panel._on_file_node_double_clicked(0, (dpg.mvMouseButton_Left, 0), (self._node(recording), 0))

        assert app._main_tab._converter_logic.gathered_paths == (recording,)

    def _recording(self, tmp_path: Path) -> Path:
        return self._tree(tmp_path) / "one.wav"

    @staticmethod
    def _node(recording: Path) -> FileSystemNode:
        return FileSystemNode(recording.name, node_type=NodeType.FILE, filepath=recording)


class TestConverterStemsCard:
    """Gathering recordings paints the converter card: a row each, carrying what the reader set."""

    def _gather(self, app: Application, tmp_path: Path, names: List[str]) -> List[Path]:
        paths = []
        for name in names:
            path = tmp_path / name
            path.touch()
            paths.append(path)

        converter_logic = app._main_tab._converter_logic
        converter_logic.set_output(OutputKind.MIXED)
        converter_logic.gather_recordings(paths)
        return paths

    def test_a_row_is_built_for_every_recording(self, app: Application, tmp_path: Path) -> None:
        paths = self._gather(app, tmp_path, ["a.wav", "b.wav"])

        for path in paths:
            assert dpg.does_item_exist(stems_list(app).tags.row(str(path), SUF_GROUP))
            assert dpg.does_item_exist(stems_list(app).tags.row(str(path), SUF_BUTTON))

    def test_a_rows_channels_show_what_was_set(self, app: Application, tmp_path: Path) -> None:
        """The row offers a checkbox per channel the configuration enables, ticked as the row holds it."""
        path = self._gather(app, tmp_path, ["a.wav"])[0]
        converter_logic = app._main_tab._converter_logic
        enabled = app.session_manager.converter_settings.channels
        kept, cleared = enabled[-1], enabled[0]

        converter_logic.set_source_channels(path, frozenset({kept}))

        assert dpg.get_value(stems_list(app).tags.channel(str(path), kept)) is True
        assert dpg.get_value(stems_list(app).tags.channel(str(path), cleared)) is False

    def test_removing_a_recording_takes_its_row_with_it(self, app: Application, tmp_path: Path) -> None:
        first, second = self._gather(app, tmp_path, ["a.wav", "b.wav"])

        app._main_tab._converter_logic.remove_source(first)

        assert not dpg.does_item_exist(stems_list(app).tags.row(str(first), SUF_GROUP))
        assert dpg.does_item_exist(stems_list(app).tags.row(str(second), SUF_GROUP))

    def test_the_list_stands_whichever_run_the_switch_names(self, app: Application, tmp_path: Path) -> None:
        """The gathered sources are what a run converts either way, so the list is always on screen."""
        path = self._gather(app, tmp_path, ["a.wav"])[0]
        assert dpg.get_item_configuration(TAG_MAIN_CONVERTER_WINDOW_STEMS)["show"] is True

        app._main_tab._converter_logic.set_output(OutputKind.PER_RECORDING)

        assert dpg.get_item_configuration(TAG_MAIN_CONVERTER_WINDOW_STEMS)["show"] is True
        assert dpg.does_item_exist(stems_list(app).tags.row(str(path), SUF_GROUP))

    def test_the_list_stays_on_screen_while_a_conversion_runs(self, app: Application, tmp_path: Path) -> None:
        """The setup is what a running conversion is making, so it keeps saying what that is."""
        path = self._gather(app, tmp_path, ["a.wav"])[0]

        _reports_running(app, "running", 0.5)

        assert dpg.get_item_configuration(TAG_MAIN_CONVERTER_WINDOW_STEMS)["show"] is True
        assert dpg.get_item_configuration(stems_list(app).tags.row(str(path), SUF_BUTTON))["enabled"] is False

    def test_a_level_draws_its_own_band(self, app: Application, tmp_path: Path) -> None:
        first, second = self._gather(app, tmp_path, ["a.wav", "b.wav"])
        converter_logic = app._main_tab._converter_logic

        converter_logic.isolate_source(second)

        assert dpg.does_item_exist(stems_list(app).tags.level(0, SUF_TABLE))
        assert dpg.does_item_exist(stems_list(app).tags.level(1, SUF_TABLE))
        assert dpg.does_item_exist(stems_list(app).tags.level(2, SUF_STRIP))
        assert dpg.get_item_parent(stems_list(app).tags.row(str(first), SUF_GROUP)) == stems_list(app).tags.level(
            0, SUF_TABLE
        )
        assert dpg.get_item_parent(stems_list(app).tags.row(str(second), SUF_GROUP)) == stems_list(app).tags.level(
            1, SUF_TABLE
        )

    def test_a_row_is_the_thing_you_drag_it_by(self, app: Application, tmp_path: Path) -> None:
        """A level is a turn to choose, so the drag that rearranges them arrives with the second."""
        first, _second = self._gather(app, tmp_path, ["a.wav", "b.wav"])

        assert dpg.get_item_children(stems_list(app).tags.row(str(first), SUF_TEXT), DRAG_PAYLOAD_SLOT)

    def test_one_recording_in_a_mix_is_its_own_order(self, app: Application, tmp_path: Path) -> None:
        path = self._gather(app, tmp_path, ["a.wav"])[0]

        assert not dpg.does_item_exist(stems_list(app).tags.level(0, SUF_TEXT))
        assert not dpg.get_item_children(stems_list(app).tags.row(str(path), SUF_TEXT), DRAG_PAYLOAD_SLOT)

    def test_dropping_a_recording_on_a_row_joins_that_rows_level(self, app: Application, tmp_path: Path) -> None:
        first, second = self._gather(app, tmp_path, ["a.wav", "b.wav"])
        converter_logic = app._main_tab._converter_logic
        converter_logic.isolate_source(second)

        drop(stems_list(app).tags.row(str(second), SUF_TEXT), str(first))

        assert _level_of(app, first) == _level_of(app, second)
        assert not dpg.does_item_exist(stems_list(app).tags.level(1, SUF_TABLE))

    def test_dropping_a_recording_in_a_gap_opens_a_level(self, app: Application, tmp_path: Path) -> None:
        first, _second = self._gather(app, tmp_path, ["a.wav", "b.wav"])

        drop(stems_list(app).tags.level(1, SUF_STRIP), str(first))

        assert dpg.does_item_exist(stems_list(app).tags.level(1, SUF_TABLE))
        assert _level_of(app, first) == stems_list(app).tags.level(1, SUF_TABLE)

    def test_a_clicked_row_is_what_the_settings_card_edits(self, app: Application, tmp_path: Path) -> None:
        """The whole wiring chain: a click on a row, a box on the card, and the row it settles.

        A recording joins holding the channels a run hands out, so the box the case ticks is one
        of the two it starts without.
        """
        first, second = self._gather(app, tmp_path, ["a.wav", "b.wav"])
        assert ChannelName.PULSE2 not in _row_of(app, second).channels

        _click_row(app, second)
        _click_slot_box(SettingsField.CHANNELS, ChannelName.PULSE2)

        assert ChannelName.PULSE2 in _row_of(app, second).channels
        assert ChannelName.PULSE2 not in _row_of(app, first).channels

    def _gather_folder(self, app: Application, tmp_path: Path, names: List[str]) -> List[Path]:
        """Gathers a folder of recordings as one row, and answers what it holds."""
        root = tmp_path / "takes"
        root.mkdir()
        paths = []
        for name in names:
            path = root / name
            path.touch()
            paths.append(path)

        converter_logic = app._main_tab._converter_logic
        converter_logic.set_output(OutputKind.PER_RECORDING)
        converter_logic.gather_folder(root, get_audio_files(root, sort=True))
        return paths

    def test_a_folder_arrives_closed_and_opens_onto_what_it_holds(
        self,
        app: Application,
        tmp_path: Path,
    ) -> None:
        held = self._gather_folder(app, tmp_path, ["a.wav", "b.wav"])
        root = held[0].parent
        name_tag = stems_list(app).tags.row(str(held[0]), SUF_TEXT)
        assert not dpg.does_item_exist(name_tag)

        stems_list(app).toggle_folder(str(root))

        assert dpg.does_item_exist(name_tag)
        assert dpg.does_item_exist(stems_list(app).tags.region(str(root)))

    def test_a_recording_inside_an_open_folder_is_what_the_card_edits(
        self,
        app: Application,
        tmp_path: Path,
    ) -> None:
        """A reader who opens a folder answers for one of its recordings without breaking it up."""
        first, second = self._gather_folder(app, tmp_path, ["a.wav", "b.wav"])
        stems_list(app).toggle_folder(str(first.parent))
        assert ChannelName.PULSE2 not in _row_of(app, second).channels

        _click_row(app, second)
        _click_slot_box(SettingsField.CHANNELS, ChannelName.PULSE2)

        assert ChannelName.PULSE2 in _row_of(app, second).channels
        assert ChannelName.PULSE2 not in _row_of(app, first).channels

    def test_the_card_names_the_gesture_that_gives_it_a_row(self, app: Application, tmp_path: Path) -> None:
        """The card answers for a picked row, so with none picked it says which gesture picks one."""
        self._gather(app, tmp_path, ["a.wav"])

        assert dpg.get_item_configuration(TAG_MAIN_SOURCE_TEXT_UNPICKED)["show"] is True
        assert dpg.get_item_configuration(TAG_MAIN_SOURCE_GROUP_GRID)["show"] is False

    def test_a_picked_row_brings_the_grid_with_it(self, app: Application, tmp_path: Path) -> None:
        path = self._gather(app, tmp_path, ["a.wav"])[0]

        _click_row(app, path)

        assert dpg.get_item_configuration(TAG_MAIN_SOURCE_GROUP_GRID)["show"] is True
        assert dpg.get_value(TAG_MAIN_SOURCE_TEXT_INSPECTING) == path.stem

    def test_the_run_controls_arrive_with_the_first_recording(self, app: Application, tmp_path: Path) -> None:
        """The choices answer for what is listed, so they stand once there is something to answer for."""
        assert dpg.get_item_configuration(TAG_MAIN_CONVERTER_GROUP_CONTROLS)["show"] is False

        self._gather(app, tmp_path, ["a.wav"])

        assert dpg.get_item_configuration(TAG_MAIN_CONVERTER_GROUP_CONTROLS)["show"] is True

    def test_the_order_arrives_with_the_second_recording_in_a_mix(self, app: Application, tmp_path: Path) -> None:
        """One recording is its own order, so the choice of how levels take turns arrives with the second."""
        self._gather(app, tmp_path, ["a.wav"])
        assert dpg.get_item_configuration(TAG_MAIN_CONVERTER_GROUP_ORDER)["show"] is False

        self._gather(app, tmp_path, ["b.wav"])

        assert dpg.get_item_configuration(TAG_MAIN_CONVERTER_GROUP_ORDER)["show"] is True

    def test_the_order_explanation_leaves_with_the_control_it_belongs_to(
        self,
        app: Application,
        tmp_path: Path,
    ) -> None:
        """A tooltip left live over a hidden widget's rectangle explains whatever moved into it."""
        self._gather(app, tmp_path, ["a.wav", "b.wav"])
        assert dpg.get_item_configuration(TAG_MAIN_CONVERTER_TOOLTIP_HIERARCHY_MODE)["show"] is True

        app._main_tab._converter_logic.set_output(OutputKind.PER_RECORDING)

        assert dpg.get_item_configuration(TAG_MAIN_CONVERTER_TOOLTIP_HIERARCHY_MODE)["show"] is False

    def test_a_recording_holding_no_channel_grays_out_but_stays_listed(
        self,
        app: Application,
        tmp_path: Path,
    ) -> None:
        path = self._gather(app, tmp_path, ["a.wav"])[0]

        app._main_tab._converter_logic.set_source_channels(path, frozenset())

        name_tag = stems_list(app).tags.row(str(path), SUF_TEXT)
        assert dpg.does_item_exist(stems_list(app).tags.row(str(path), SUF_GROUP))
        assert dpg.get_item_alias(dpg.get_item_theme(name_tag)) == TAG_GLOBAL_THEME_STEMS_ROW_INERT
        assert dpg.get_item_configuration(name_tag)["enabled"] is True
