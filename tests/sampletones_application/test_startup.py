from contextlib import ExitStack
from unittest.mock import patch

import dearpygui.dearpygui as dpg
import pytest

from sampletones_application.application import Application

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
    def dpg_context(self) -> None:
        dpg.create_context()
        yield
        dpg.destroy_context()

    def test_initialises_without_error(self) -> None:
        all_patches = [patch(f"dearpygui.dearpygui.{name}", return_value=None) for name in _DPG_DISPLAY_FUNCTIONS] + [
            patch("sampletones_application.utils.callbacks.queue.CallbackQueue.start"),
        ]
        with ExitStack() as stack:
            for p in all_patches:
                stack.enter_context(p)
            Application()
