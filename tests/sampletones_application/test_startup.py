from contextlib import ExitStack
from pathlib import Path
from typing import Any, Generator
from unittest.mock import patch

import dearpygui.dearpygui as dpg
import pytest

from sampletones_application.application import Application
from sampletones_application.utils.background import stop_background_workers

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
    are the recovery boundary (docs/architecture.md § Error Handling Policy). The
    recovery behaviour itself is covered by the coordinator tests.
    """

    def test_project_restore_delegates_to_coordinator(self, app: Application) -> None:
        with patch.object(app._project_coordinator, "restore") as restore:
            app._try_load_current_project(Path("last.stp"))

        restore.assert_called_once_with(Path("last.stp"))

    def test_reconstruction_restore_delegates_to_coordinator(self, app: Application) -> None:
        with patch.object(app._reconstruction_coordinator, "restore") as restore:
            app._try_load_current_reconstruction(Path("last.stn"))

        restore.assert_called_once_with(Path("last.stn"))
