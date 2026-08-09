from contextlib import ExitStack
from pathlib import Path
from typing import Any, Callable, Dict, Final, Generator, List
from unittest.mock import PropertyMock, patch

import dearpygui.dearpygui as dpg
import pytest

from sampletones_application.application import Application
from sampletones_application.config.managers.session import SessionManager
from sampletones_application.logic.history.action import HistoryAction
from sampletones_application.utils.gui.shortcuts.ids import ShortcutId
from sampletones_application.utils.parallelization.background import (
    stop_background_workers,
)
from sampletones_application.utils.parallelization.thread import SingleThreadExecutor
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


class TestGUIStartup:
    @pytest.fixture(autouse=True)
    def dpg_context(self) -> Generator[Any, Application, Any]:
        dpg.create_context()
        yield
        stop_background_workers()
        SingleThreadExecutor.reset_shutdown()
        dpg.destroy_context()

    def test_initialises_without_error(self) -> None:
        with ExitStack() as stack:
            for p in _display_patches():
                stack.enter_context(p)

            Application()


@pytest.fixture
def app() -> Generator[Any, Application, Any]:
    dpg.create_context()
    try:
        with ExitStack() as stack:
            for p in _display_patches():
                stack.enter_context(p)
            yield Application()
    finally:
        stop_background_workers()
        SingleThreadExecutor.reset_shutdown()
        dpg.destroy_context()


class TestKeybindingPreferences:
    """The application runs on the keys the session stores, which is what makes a rebind stick."""

    @pytest.fixture
    def application(self) -> Generator[Any, Application, Any]:
        dpg.create_context()
        try:
            with ExitStack() as stack:
                for display_patch in _display_patches():
                    stack.enter_context(display_patch)

                stack.enter_context(
                    patch.object(
                        SessionManager,
                        "shortcut_overrides",
                        new_callable=PropertyMock,
                        return_value=REBOUND_UNDO,
                    )
                )
                yield Application()
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
        source_before = app.reconstruction_manager.audio_filepath

        app._add_current_reconstruction_to_sequencer()

        assert source_before is not None
        assert app.reconstruction_manager.audio_filepath == source_before
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
        assert sample.reconstruction.audio_filepath is None
        assert not app._editing_project_sample()
