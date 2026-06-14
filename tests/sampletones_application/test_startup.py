from contextlib import ExitStack
from pathlib import Path
from typing import Any, Generator
from unittest.mock import patch

import dearpygui.dearpygui as dpg
import pytest

from sampletones_application.application import Application
from sampletones_shared.exceptions import NotAValidArchiveError

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
    "set_exit_callback",
    "set_primary_window",
]


class TestGUIStartup:
    @pytest.fixture(autouse=True)
    def dpg_context(self) -> Generator[Any, Application, Any]:
        dpg.create_context()
        yield
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
        dpg.destroy_context()


class TestStartupLoadResilience:
    """Startup auto-load behaviour, per docs/architecture.md (§ Error Handling Policy).

    The reconstruction handler forwards to the ReconstructionCoordinator — the recovery
    boundary that catches load failures and notifies the user; Application does not
    recover there. The project handler still loads via the controller and resets the
    session on failure (a known asymmetry: the project coordinator's interactive
    open-with-confirmation flow is unsuitable for a silent startup restore).
    """

    def test_failed_project_load_resets_to_none(self, app: Application) -> None:
        with (
            patch.object(
                app.project_manager,
                "load",
                side_effect=NotAValidArchiveError("bad archive"),
            ),
            patch.object(app.session_manager, "set_current_project") as reset,
        ):
            app._try_load_current_project(Path("missing.stp"))

        reset.assert_called_once_with(None)

    def test_oserror_project_load_resets_to_none(self, app: Application) -> None:
        with (
            patch.object(
                app.project_manager,
                "load",
                side_effect=FileNotFoundError("missing"),
            ),
            patch.object(app.session_manager, "set_current_project") as reset,
        ):
            app._try_load_current_project(Path("missing.stp"))

        reset.assert_called_once_with(None)

    def test_reconstruction_restore_delegates_to_coordinator(self, app: Application) -> None:
        # Application only forwards the startup restore; recovery (catching the failure
        # and informing the user) is the reconstruction coordinator's responsibility.
        with patch.object(app._reconstruction_coordinator, "load_with_confirmation") as load:
            app._try_load_current_reconstruction(Path("last.stn"))

        load.assert_called_once_with(Path("last.stn"))

    def test_unexpected_error_propagates(self, app: Application) -> None:
        with patch.object(
            app.project_manager,
            "load",
            side_effect=RuntimeError("runtime_error"),
        ):
            with pytest.raises(RuntimeError):
                app._try_load_current_project(Path("missing.stp"))
