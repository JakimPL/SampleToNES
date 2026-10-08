from pathlib import Path

from automation.screen import Screen
from automation.worlds.home import HomeFile, World, screen_filling_state
from sampletones_application.config.session.state.state import ApplicationState
from sampletones_application.utils.gui.shortcuts.ids import ShortcutId
from tests.screens.application.restart.constants import RECORDING_FREQUENCY, RECORDING_NAME, RECORDING_SECONDS
from tests.suite.screens.seeds.recordings import Recording


def home_folder(name: str) -> Path:
    """A folder of the home the application was started in."""
    return Path.cwd() / name


def recording_in(folder: str) -> HomeFile:
    """A short recording placed in ``folder`` of the home."""
    return Recording(
        destination=home_folder(folder) / RECORDING_NAME,
        seconds=RECORDING_SECONDS,
        frequency=RECORDING_FREQUENCY,
    )


def leave(screen: Screen) -> None:
    """Leaves through Exit, which writes the session, and waits for the application to stop."""
    screen.press_shortcut(ShortcutId.EXIT)

    assert screen.wait_for_exit()


def world_with(state: ApplicationState, *files: HomeFile) -> World:
    """A home with ``state`` as its session and ``files``."""
    return World(
        state=state,
        application_config=None,
        config=None,
        files=files,
    )


def state_with_advanced(shown: bool) -> ApplicationState:
    """A screen-filling session with Advanced settings shown or hidden as ``shown`` says."""
    return screen_filling_state().model_copy(update={"advanced_settings": shown})
