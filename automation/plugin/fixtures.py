import os
from pathlib import Path
from typing import Final, Iterator

import pytest

from automation.application.boundaries import Boundaries
from automation.application.running import ScreenApplication
from automation.application.startup import Startup
from automation.boundaries.audio import (
    OutputDevice,
    OutputRecord,
    provide_output_device,
)
from automation.boundaries.dialogs import ScriptedFileDialogs
from automation.boundaries.errors import ErrorRecords
from automation.boundaries.highlights import TableHighlights
from automation.boundaries.reveals import FileManagerStandIn
from automation.boundaries.spawns import SpawnGuard
from automation.dearpygui.bridge import Bridge
from automation.dearpygui.display import VirtualDisplay
from automation.dearpygui.hand import Hand
from automation.dearpygui.windows import WindowManager
from automation.dearpygui.xtest import XTestDevice
from automation.environment import (
    ARTIFACTS_VARIABLE,
    display_backend,
    screen_size,
)
from automation.holds.base import Holds
from automation.paths import FAILURE_SCREENSHOT
from automation.plugin.constants import DISPLAY_KEY
from automation.render_thread import QueueRenderThread
from automation.screen import Screen
from automation.worlds.home import World, lived_in_world
from sampletones_application.application import Application
from sampletones_application.config.profile import UserProfile

ANSWER_TIMEOUT_SECONDS: Final[float] = 30.0
STAND_IN_PROGRAMS: Final[str] = "programs"
REVEALS_FILE: Final[str] = "reveals.log"
DISPLAY_NAME_KEY: Final[pytest.StashKey[str]] = pytest.StashKey()


@pytest.fixture(name="world")
def world_fixture() -> World:
    """What the scenario's home holds as the application starts; a scenario overrides it to seed its own."""
    return lived_in_world()


@pytest.fixture(name="startup")
def startup_fixture() -> Startup:
    """The documents the application opens as it starts; a scenario overrides it to open its own."""
    return Startup(
        reconstruction=None,
        project=None,
    )


@pytest.fixture(name="output_device")
def output_device_fixture() -> OutputDevice:
    """The output the scenario's machine offers; a scenario overrides it to start with none."""
    return OutputDevice.SILENT


@pytest.fixture(name="screen_render_thread")
def screen_render_thread_fixture() -> QueueRenderThread:
    """The queue-backed render thread the scenario's application and bridge share."""
    return QueueRenderThread()


@pytest.fixture(name="screen_bridge")
def screen_bridge_fixture(screen_render_thread: QueueRenderThread) -> Bridge:
    """The bridge through which a scenario asks the render thread for readings and gestures."""
    return Bridge(screen_render_thread, answer_timeout=ANSWER_TIMEOUT_SECONDS)


@pytest.fixture(name="screen_boundaries")
def screen_boundaries_fixture(
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
    output = OutputRecord()
    output.install(monkeypatch)
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
        output=output,
    )


@pytest.fixture(name="screen_application")
def screen_application_fixture(
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


@pytest.fixture(name="screen")
def screen_fixture(
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
        output=screen_boundaries.output,
        artifacts=Path(os.environ[ARTIFACTS_VARIABLE]),
    )
    window_manager.close()
    device.close()


def _worker_display(config: pytest.Config) -> str:
    """The display this worker's scenarios draw on, started with the first of them."""
    name = config.stash.get(DISPLAY_NAME_KEY, None)
    if name is not None:
        return name

    display = VirtualDisplay(display_backend(os.environ), screen_size(os.environ))
    name = display.start()
    config.stash[DISPLAY_KEY] = display
    config.stash[DISPLAY_NAME_KEY] = name
    return name
