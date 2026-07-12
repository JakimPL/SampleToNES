from contextlib import ExitStack
from pathlib import Path
from typing import Any, Callable, Generator
from unittest.mock import patch

import dearpygui.dearpygui as dpg
import pytest

from sampletones_application.application import Application
from sampletones_application.logic.history.action import HistoryAction
from sampletones_application.utils.parallelization.background import stop_background_workers
from sampletones_core.reconstructions import Reconstruction

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
    "toggle_viewport_fullscreen",
    "set_exit_callback",
    "set_primary_window",
]


class TestGUIStartup:
    @pytest.fixture(autouse=True)
    def dpg_context(self) -> Generator[Any, Application, Any]:
        dpg.create_context()
        yield
        stop_background_workers()
        dpg.destroy_context()

    def test_initialises_without_error(self) -> None:
        dearpygui_patches = [patch(f"dearpygui.dearpygui.{name}", return_value=None) for name in _DPG_DISPLAY_FUNCTIONS]
        callback_patches = [patch("sampletones_application.utils.callbacks.queue.CallbackQueue.start")]
        all_patches = dearpygui_patches + callback_patches
        with ExitStack() as stack:
            for p in all_patches:
                stack.enter_context(p)

            Application()


@pytest.fixture
def app() -> Generator[Any, Application, Any]:
    dpg.create_context()
    dearpygui_patches = [patch(f"dearpygui.dearpygui.{name}", return_value=None) for name in _DPG_DISPLAY_FUNCTIONS]
    callback_patches = [patch("sampletones_application.utils.callbacks.queue.CallbackQueue.start")]
    all_patches = dearpygui_patches + callback_patches
    try:
        with ExitStack() as stack:
            for p in all_patches:
                stack.enter_context(p)
            yield Application()
    finally:
        stop_background_workers()
        dpg.destroy_context()


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
