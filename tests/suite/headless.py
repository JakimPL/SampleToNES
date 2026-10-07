from contextlib import ExitStack, contextmanager
from pathlib import Path
from typing import Any, Final, Iterator, List, Tuple
from unittest.mock import patch

import dearpygui.dearpygui as dpg
import pytest

from sampletones_application.application import Application
from sampletones_application.config.profile import UserProfile
from sampletones_application.utils.parallelization.background import stop_background_workers
from sampletones_application.utils.parallelization.thread import SingleThreadExecutor
from sampletones_core.configs import Config
from sampletones_shared.paths.user import CONFIG_PATH, LIBRARY_DIRECTORY, RECONSTRUCTIONS_DIRECTORY

DISPLAY_FUNCTIONS: Final[Tuple[str, ...]] = (
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
)
VIEWPORT_CLIENT_WIDTH: Final[int] = 1280
VIEWPORT_CLIENT_HEIGHT: Final[int] = 720


def display_patches() -> List[Any]:
    """The display calls a headless run stands in for, and the queue it keeps from starting."""
    patches = [patch(f"dearpygui.dearpygui.{name}", return_value=None) for name in DISPLAY_FUNCTIONS]
    patches.append(
        patch(
            "dearpygui.dearpygui.get_viewport_client_width",
            return_value=VIEWPORT_CLIENT_WIDTH,
        )
    )
    patches.append(
        patch(
            "dearpygui.dearpygui.get_viewport_client_height",
            return_value=VIEWPORT_CLIENT_HEIGHT,
        )
    )
    patches.append(patch("sampletones_application.utils.callbacks.queue.CallbackQueue.start"))
    return patches


def profile_in(directory: Path) -> UserProfile:
    """Starts the application on a profile of its own, in the state a first run finds.

    The settings and the keys an application comes up on are read from its profile, so a suite
    given the user's own answers for whatever that machine prefers. A directory per test is what
    holds a run to the shipped defaults.
    """
    return UserProfile(
        config=directory / "config.yaml",
        state=directory / "state.yaml",
    )


def settings_in(directory: Path) -> Path:
    """Writes the settings a run starts on: the shipped defaults, with the instruction library and
    the reconstructions held in the test's own directory.

    A startup lists the reconstructions and loads the library from the directories its settings
    name, so a run reads only the files a test places beside it.
    """
    config = Config()
    general = config.general.model_copy(
        update={
            "library_directory": str(directory / LIBRARY_DIRECTORY.name),
            "reconstructions_directory": str(directory / RECONSTRUCTIONS_DIRECTORY.name),
        }
    )
    path = directory / CONFIG_PATH.name
    config.model_copy(update={"general": general}).save(path)
    return path


def headless_application(directory: Path) -> Application:
    """The whole application on a profile and settings of its own in ``directory``."""
    return Application(profile=profile_in(directory), config_path=settings_in(directory))


@contextmanager
def headless_context() -> Iterator[None]:
    """A DearPyGui context with the display stood in, torn down with the workers a run started."""
    dpg.create_context()
    try:
        with ExitStack() as stack:
            for display_patch in display_patches():
                stack.enter_context(display_patch)

            yield
    finally:
        stop_background_workers()
        SingleThreadExecutor.reset_shutdown()
        dpg.destroy_context()


@pytest.fixture
def app(tmp_path: Path) -> Iterator[Application]:
    """The whole application built headless on a profile of the case's own."""
    with headless_context():
        yield headless_application(tmp_path)
