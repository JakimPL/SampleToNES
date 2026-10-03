import os
from pathlib import Path
from typing import Final, Iterator

import pytest

from sampletones_application.application import Application
from sampletones_application.config.profile import UserProfile
from tests.suite.screens.application.boundaries import Boundaries
from tests.suite.screens.application.running import ScreenApplication
from tests.suite.screens.application.startup import Startup
from tests.suite.screens.boundaries.audio import OutputDevice, provide_output_device
from tests.suite.screens.boundaries.dialogs import ScriptedFileDialogs
from tests.suite.screens.boundaries.errors import ErrorRecords
from tests.suite.screens.boundaries.highlights import TableHighlights
from tests.suite.screens.boundaries.reveals import FileManagerStandIn
from tests.suite.screens.boundaries.spawns import SpawnGuard
from tests.suite.screens.dearpygui.bridge import Bridge
from tests.suite.screens.dearpygui.display import VirtualDisplay
from tests.suite.screens.dearpygui.hand import Hand
from tests.suite.screens.dearpygui.windows import WindowManager
from tests.suite.screens.dearpygui.xtest import XTestDevice
from tests.suite.screens.environment import ARTIFACTS_VARIABLE, SCREEN_SIZE, display_backend
from tests.suite.screens.holds.base import Holds
from tests.suite.screens.paths import FAILURE_SCREENSHOT
from tests.suite.screens.plugin.constants import DISPLAY_KEY
from tests.suite.screens.plugin.hold_fixtures import screen_holds
from tests.suite.screens.render_thread import QueueRenderThread
from tests.suite.screens.screen import Screen
from tests.suite.screens.worlds.home import World
from tests.suite.screens.worlds.recordings import lived_in_world

ANSWER_TIMEOUT_SECONDS: Final[float] = 30.0
STAND_IN_PROGRAMS: Final[str] = "programs"
REVEALS_FILE: Final[str] = "reveals.log"
DISPLAY_NAME_KEY: Final[pytest.StashKey[str]] = pytest.StashKey()


@pytest.fixture
def world() -> World:
    """What the scenario's home holds as the application starts; a scenario overrides it to seed its own."""
    return lived_in_world()


@pytest.fixture
def startup() -> Startup:
    """The documents the application opens as it starts; a scenario overrides it to open its own."""
    return Startup(
        reconstruction=None,
        project=None,
    )


@pytest.fixture
def output_device() -> OutputDevice:
    """The output the scenario's machine offers; a scenario overrides it to start with none."""
    return OutputDevice.SILENT


@pytest.fixture
def screen_render_thread() -> QueueRenderThread:
    """The queue-backed render thread the scenario's application and bridge share."""
    return QueueRenderThread()


@pytest.fixture
def screen_bridge(screen_render_thread: QueueRenderThread) -> Bridge:
    """The bridge through which a scenario asks the render thread for readings and gestures."""
    return Bridge(screen_render_thread, answer_timeout=ANSWER_TIMEOUT_SECONDS)


@pytest.fixture
def screen_boundaries(
    output_device: OutputDevice,
    screen_holds: Holds,
    monkeypatch: pytest.MonkeyPatch,
) -> Boundaries:
    """Puts the scenario's stand-ins between the application and the desktop before it starts."""
    dialogs = ScriptedFileDialogs()
    dialogs.install(monkeypatch)
    errors = ErrorRecords()
    errors.install()
    artifacts = Path(os.environ[ARTIFACTS_VARIABLE])
    file_manager = FileManagerStandIn(artifacts / STAND_IN_PROGRAMS, artifacts / REVEALS_FILE)
    file_manager.install(monkeypatch)
    spawns = SpawnGuard()
    spawns.install()
    spawns.allow(file_manager.folder)
    highlights = TableHighlights()
    highlights.install(monkeypatch)
    provide_output_device(
        output_device,
        home=Path.home(),
        monkeypatch=monkeypatch,
    )
    return Boundaries(
        dialogs=dialogs,
        errors=errors,
        spawns=spawns,
        holds=screen_holds,
        file_manager=file_manager,
        highlights=highlights,
    )


@pytest.fixture
def screen_application(
    world: World,
    startup: Startup,
    screen_render_thread: QueueRenderThread,
    screen_bridge: Bridge,
    screen_boundaries: Boundaries,
) -> ScreenApplication:
    """SampleToNES as ``sampletones open`` starts it, on the scenario's display and in its home."""
    profile = UserProfile.user()
    world.write(profile)
    application = Application(
        profile=profile,
        reconstruction_path=startup.reconstruction,
        project_path=startup.project,
    )
    return ScreenApplication(
        application,
        render_thread=screen_render_thread,
        bridge=screen_bridge,
        boundaries=screen_boundaries,
        failure_screenshot=Path(os.environ[ARTIFACTS_VARIABLE]) / FAILURE_SCREENSHOT,
        state_path=profile.state,
    )


@pytest.fixture
def screen(
    screen_application: ScreenApplication,
    screen_render_thread: QueueRenderThread,
    screen_bridge: Bridge,
    screen_boundaries: Boundaries,
) -> Iterator[Screen]:
    """The application the scenario drives, with a user's hand on its display."""
    device = XTestDevice(os.environ["DISPLAY"])
    window_manager = WindowManager(os.environ["DISPLAY"], os.getpid())
    yield Screen(
        bridge=screen_bridge,
        render_thread=screen_render_thread,
        hand=Hand(screen_bridge, device),
        window_manager=window_manager,
        language=screen_application.language,
        shortcuts=screen_application.shortcuts,
        dialogs=screen_boundaries.dialogs,
        errors=screen_boundaries.errors,
        file_manager=screen_boundaries.file_manager,
        highlights=screen_boundaries.highlights,
        artifacts=Path(os.environ[ARTIFACTS_VARIABLE]),
    )
    window_manager.close()
    device.close()


def _worker_display(config: pytest.Config) -> str:
    """The display this worker's scenarios draw on, started with the first of them."""
    name = config.stash.get(DISPLAY_NAME_KEY, None)
    if name is not None:
        return name

    display = VirtualDisplay(display_backend(os.environ), SCREEN_SIZE)
    name = display.start()
    config.stash[DISPLAY_KEY] = display
    config.stash[DISPLAY_NAME_KEY] = name
    return name
