from contextlib import ExitStack, contextmanager
from pathlib import Path
from typing import Any, Callable, Dict, Final, Generator, List
from unittest.mock import PropertyMock, patch

import dearpygui.dearpygui as dpg
import pytest

from sampletones_application.application import Application
from sampletones_application.categories.hierarchy import Tab
from sampletones_application.config.managers.session import SessionManager
from sampletones_application.config.profile import UserProfile
from sampletones_application.constants.keybindings import DEFAULT_SCHEME_NAME
from sampletones_application.logic.history.action import HistoryAction
from sampletones_application.tags.general import (
    SUF_BUTTON,
    SUF_GROUP,
    SUF_HANDLE,
    SUF_STRIP,
    SUF_TABLE,
    SUF_TEXT,
)
from sampletones_application.tags.main import (
    TAG_MAIN_CONVERTER_TOOLTIP_HIERARCHY_MODE,
    TAG_MAIN_CONVERTER_WINDOW_STEMS,
)
from sampletones_application.ui.panels.main.converter import GUIConverterPanel
from sampletones_application.utils.gui.keyboard.event import KeyEvent
from sampletones_application.utils.gui.shortcuts.ids import (
    CHANNEL_SHORTCUT_IDS,
    TAB_SHORTCUT_IDS,
    ShortcutId,
)
from sampletones_application.utils.parallelization.background import (
    stop_background_workers,
)
from sampletones_application.utils.parallelization.thread import SingleThreadExecutor
from sampletones_application.view_model.main.converter import ConversionPhase
from sampletones_core.constants.enums import ChannelName
from sampletones_core.reconstructions import Reconstruction

REBOUND_UNDO: Final[Dict[str, str]] = {"Undo": "Ctrl+Alt+U"}

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

    def test_initialises_without_error(self, tmp_path: Path) -> None:
        with ExitStack() as stack:
            for display_patch in _display_patches():
                stack.enter_context(display_patch)

            Application(profile=_profile(tmp_path))

    def test_initialises_where_nothing_can_play(self, tmp_path: Path) -> None:
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
    recovery behaviour itself is covered by the coordinator tests.
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
        app._edit_project_sample(sample.id)
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
        assert original in [sample.reconstruction for sample in app.project_manager.current.samples]


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

        sample = app.project_manager.current.samples[0]
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

    def test_the_main_tab_switches_the_generator_a_reconstruction_is_built_from(self, app: Application) -> None:
        selected = frozenset(app.config_manager.config.generation.channels)

        self._press(app, ChannelName.TRIANGLE, Tab.MAIN)

        assert frozenset(app.config_manager.config.generation.channels) == selected ^ {ChannelName.TRIANGLE}

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


class TestConverterStemsCard:
    """Gathering recordings paints the converter card: a row each, carrying what the reader set."""

    def _gather(self, app: Application, tmp_path: Path, names: List[str]) -> List[Path]:
        paths = []
        for name in names:
            path = tmp_path / name
            path.touch()
            paths.append(path)

        converter_logic = app._main_tab._converter_logic
        converter_logic.set_stems_mode(True)
        converter_logic.add_sources(paths)
        return paths

    def test_a_row_is_built_for_every_recording(self, app: Application, tmp_path: Path) -> None:
        paths = self._gather(app, tmp_path, ["a.wav", "b.wav"])

        for path in paths:
            assert dpg.does_item_exist(GUIConverterPanel._row_tag(path, SUF_GROUP))
            assert dpg.does_item_exist(GUIConverterPanel._row_tag(path, SUF_BUTTON))

    def test_a_rows_channels_show_what_was_set(self, app: Application, tmp_path: Path) -> None:
        """The row offers a checkbox per channel the configuration enables, ticked as the row holds it."""
        path = self._gather(app, tmp_path, ["a.wav"])[0]
        converter_logic = app._main_tab._converter_logic
        enabled = list(converter_logic._config_manager.config.generation.channels)
        kept, cleared = enabled[-1], enabled[0]

        converter_logic.set_source_channels(path, frozenset({kept}))

        assert dpg.get_value(GUIConverterPanel._channel_tag(path, kept)) is True
        assert dpg.get_value(GUIConverterPanel._channel_tag(path, cleared)) is False

    def test_removing_a_recording_takes_its_row_with_it(self, app: Application, tmp_path: Path) -> None:
        first, second = self._gather(app, tmp_path, ["a.wav", "b.wav"])

        app._main_tab._converter_logic.remove_source(first)

        assert not dpg.does_item_exist(GUIConverterPanel._row_tag(first, SUF_GROUP))
        assert dpg.does_item_exist(GUIConverterPanel._row_tag(second, SUF_GROUP))

    def test_leaving_stems_mode_hides_the_list(self, app: Application, tmp_path: Path) -> None:
        self._gather(app, tmp_path, ["a.wav"])
        assert dpg.get_item_configuration(TAG_MAIN_CONVERTER_WINDOW_STEMS)["show"] is True

        app._main_tab._converter_logic.set_stems_mode(False)

        assert dpg.get_item_configuration(TAG_MAIN_CONVERTER_WINDOW_STEMS)["show"] is False

    def test_the_list_stays_on_screen_while_a_conversion_runs(self, app: Application, tmp_path: Path) -> None:
        """The setup is what a running conversion is making, so it keeps saying what that is."""
        path = self._gather(app, tmp_path, ["a.wav"])[0]
        converter_logic = app._main_tab._converter_logic

        converter_logic._phase = ConversionPhase.RUNNING
        converter_logic.refresh_view()
        converter_logic._emit_view_model("running", 0.5)

        assert dpg.get_item_configuration(TAG_MAIN_CONVERTER_WINDOW_STEMS)["show"] is True
        assert dpg.get_item_configuration(GUIConverterPanel._row_tag(path, SUF_BUTTON))["enabled"] is False

    def test_a_level_draws_its_own_band(self, app: Application, tmp_path: Path) -> None:
        first, second = self._gather(app, tmp_path, ["a.wav", "b.wav"])
        converter_logic = app._main_tab._converter_logic

        converter_logic.isolate_source(second)

        assert dpg.does_item_exist(GUIConverterPanel._level_tag(0, SUF_TABLE))
        assert dpg.does_item_exist(GUIConverterPanel._level_tag(1, SUF_TABLE))
        assert dpg.does_item_exist(GUIConverterPanel._level_tag(2, SUF_STRIP))
        assert dpg.get_item_parent(GUIConverterPanel._row_tag(first, SUF_GROUP)) == GUIConverterPanel._level_tag(
            0, SUF_TABLE
        )
        assert dpg.get_item_parent(GUIConverterPanel._row_tag(second, SUF_GROUP)) == GUIConverterPanel._level_tag(
            1, SUF_TABLE
        )

    def test_a_row_carries_a_handle_to_drag_it_by(self, app: Application, tmp_path: Path) -> None:
        path = self._gather(app, tmp_path, ["a.wav"])[0]

        assert dpg.does_item_exist(GUIConverterPanel._row_tag(path, SUF_HANDLE))

    def test_dropping_a_recording_on_a_row_joins_that_rows_level(self, app: Application, tmp_path: Path) -> None:
        first, second = self._gather(app, tmp_path, ["a.wav", "b.wav"])
        converter_logic = app._main_tab._converter_logic
        converter_logic.isolate_source(second)

        panel = app._main_tab._converter_panel
        panel._on_dropped_on_source(dpg.get_alias_id(GUIConverterPanel._row_tag(second, SUF_TEXT)), str(first))

        assert converter_logic._levels.level_count == 1

    def test_dropping_a_recording_in_a_gap_opens_a_level(self, app: Application, tmp_path: Path) -> None:
        first, _second = self._gather(app, tmp_path, ["a.wav", "b.wav"])
        converter_logic = app._main_tab._converter_logic

        panel = app._main_tab._converter_panel
        panel._on_dropped_on_level(dpg.get_alias_id(GUIConverterPanel._level_tag(1, SUF_STRIP)), str(first))

        assert converter_logic._levels.level_count == 2
        assert converter_logic._levels.level_of(first) == 1

    def test_the_order_explanation_leaves_with_the_control_it_belongs_to(self, app: Application) -> None:
        """A tooltip left live over a hidden widget's rectangle explains whatever moved into it."""
        converter_logic = app._main_tab._converter_logic

        converter_logic.set_stems_mode(True)
        assert dpg.get_item_configuration(TAG_MAIN_CONVERTER_TOOLTIP_HIERARCHY_MODE)["show"] is True

        converter_logic.set_stems_mode(False)
        assert dpg.get_item_configuration(TAG_MAIN_CONVERTER_TOOLTIP_HIERARCHY_MODE)["show"] is False

    def test_a_recording_holding_no_channel_greys_out_but_stays_listed(
        self,
        app: Application,
        tmp_path: Path,
    ) -> None:
        path = self._gather(app, tmp_path, ["a.wav"])[0]

        app._main_tab._converter_logic.set_source_channels(path, frozenset())

        assert dpg.does_item_exist(GUIConverterPanel._row_tag(path, SUF_GROUP))
        assert dpg.get_item_configuration(GUIConverterPanel._row_tag(path, SUF_TEXT))["enabled"] is False
