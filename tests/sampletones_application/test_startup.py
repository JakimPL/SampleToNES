from contextlib import ExitStack
from pathlib import Path
from typing import Any, Generator
from unittest.mock import patch

import dearpygui.dearpygui as dpg
import pytest

from sampletones_application.application import Application
from sampletones_shared.exceptions import (
    InvalidReconstructionValuesError,
    NotAValidArchiveError,
)

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
    """The startup auto-load handlers must reset the session to ``None`` on any known
    load failure (SampleToNESError / OSError) instead of crashing the application,
    while still letting genuinely unexpected errors propagate.
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

    def test_failed_reconstruction_load_resets_to_none(self, app: Application) -> None:
        error = InvalidReconstructionValuesError("bad values", ValueError("inner"))
        with (
            patch.object(
                app.reconstruction_manager,
                "load_reconstruction",
                side_effect=error,
            ),
            patch.object(app.session_manager, "set_current_reconstruction") as reset,
        ):
            app._try_load_current_reconstruction(Path("missing.stn"))

        reset.assert_called_once_with(None)

    def test_unexpected_error_propagates(self, app: Application) -> None:
        with patch.object(
            app.project_manager,
            "load",
            side_effect=RuntimeError("runtime_error"),
        ):
            with pytest.raises(RuntimeError):
                app._try_load_current_project(Path("missing.stp"))
