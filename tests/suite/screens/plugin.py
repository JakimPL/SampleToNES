import os
from pathlib import Path
from typing import Final, Generator, Iterator, Optional

import pytest

from sampletones_application.application import Application
from sampletones_application.config.profile import UserProfile
from sampletones_application.config.session.state.state import ApplicationState
from sampletones_application.config.session.state.window import ViewportState
from sampletones_shared.utils.serialization import save_yaml_atomic
from tests.suite.screens.application import NOTHING_TO_OPEN, Boundaries, ScreenApplication, Startup
from tests.suite.screens.boundaries.audio import OutputDevice, provide_output_device
from tests.suite.screens.boundaries.dialogs import ScriptedFileDialogs
from tests.suite.screens.boundaries.errors import ErrorRecords
from tests.suite.screens.boundaries.spawns import SpawnGuard
from tests.suite.screens.dearpygui.bridge import Bridge
from tests.suite.screens.dearpygui.display import VirtualDisplay
from tests.suite.screens.dearpygui.hand import Hand
from tests.suite.screens.dearpygui.hosting import host
from tests.suite.screens.dearpygui.isolation import ReportRecorder, run_isolated
from tests.suite.screens.dearpygui.xtest import XTestDevice
from tests.suite.screens.environment import (
    ARTIFACTS_VARIABLE,
    REPORT_VARIABLE,
    SCREEN_SIZE,
    ScenarioFolders,
    child_environment,
    display_backend,
)
from tests.suite.screens.paths import FAILURE_SCREENSHOT, SCREENS_DIRECTORY
from tests.suite.screens.render_thread import QueueRenderThread
from tests.suite.screens.screen import Screen

CHILD_TIMEOUT_SECONDS: Final[float] = 180.0
ANSWER_TIMEOUT_SECONDS: Final[float] = 30.0
JOIN_TIMEOUT_SECONDS: Final[float] = 30.0
REPORT_RECORDER_NAME: Final[str] = "screens-report-recorder"
SCREEN_APPLICATION_FIXTURE: Final[str] = "screen_application"
DISPLAY_KEY: Final[pytest.StashKey[VirtualDisplay]] = pytest.StashKey()
DISPLAY_NAME_KEY: Final[pytest.StashKey[str]] = pytest.StashKey()


class ScreenScenarioError(AssertionError):
    """Raised when a screen scenario is written in a way the tier cannot host."""


def is_screen_item(item: pytest.Item) -> bool:
    """Whether ``item`` is a screen scenario, which is any test under ``tests/screens``."""
    return Path(item.path).is_relative_to(SCREENS_DIRECTORY)


def is_child_process() -> bool:
    """Whether this pytest run is the fresh process one scenario runs in."""
    return REPORT_VARIABLE in os.environ


@pytest.hookimpl(tryfirst=True)
def pytest_runtest_protocol(
    item: pytest.Item,
    nextitem: Optional[pytest.Item],
) -> Optional[bool]:
    """Runs a screen scenario in a process of its own and reports what that process reported."""
    del nextitem
    if is_child_process() or not is_screen_item(item):
        return None

    folders = ScenarioFolders.of(item.nodeid)
    folders.prepare()
    environment = child_environment(
        os.environ,
        folders,
        display=_worker_display(item.config),
    )
    item.ihook.pytest_runtest_logstart(nodeid=item.nodeid, location=item.location)
    for report in run_isolated(
        item,
        environment=environment,
        report_path=folders.reports,
        timeout=CHILD_TIMEOUT_SECONDS,
    ):
        item.ihook.pytest_runtest_logreport(report=report)

    item.ihook.pytest_runtest_logfinish(nodeid=item.nodeid, location=item.location)
    return True


def pytest_configure(config: pytest.Config) -> None:
    if is_child_process():
        recorder = ReportRecorder(config, Path(os.environ[REPORT_VARIABLE]))
        config.pluginmanager.register(recorder, REPORT_RECORDER_NAME)


def pytest_unconfigure(config: pytest.Config) -> None:
    display = config.stash.get(DISPLAY_KEY, None)
    if display is not None:
        display.stop()


@pytest.hookimpl(wrapper=True)
def pytest_pyfunc_call(pyfuncitem: pytest.Function) -> Generator[None, Optional[object], Optional[object]]:
    """Runs a screen scenario's body on a thread of its own while the application draws on this one."""
    if not is_child_process() or not is_screen_item(pyfuncitem):
        return (yield)

    loop = pyfuncitem.funcargs.get(SCREEN_APPLICATION_FIXTURE)
    if not isinstance(loop, ScreenApplication):
        raise ScreenScenarioError(f"A screen scenario takes the screen fixture: {pyfuncitem.nodeid}")

    original = pyfuncitem.obj

    def hosted(*arguments: object, **keywords: object) -> None:
        host(
            lambda: original(*arguments, **keywords),
            loop,
            join_timeout=JOIN_TIMEOUT_SECONDS,
        )

    pyfuncitem.obj = hosted
    try:
        return (yield)
    finally:
        pyfuncitem.obj = original


@pytest.fixture
def startup() -> Startup:
    """The documents the application opens as it starts; a scenario overrides it to open its own."""
    return NOTHING_TO_OPEN


@pytest.fixture
def output_device() -> OutputDevice:
    """The output the scenario's machine offers; a scenario overrides it to start with none."""
    return OutputDevice.SILENT


@pytest.fixture
def screen_render_thread() -> QueueRenderThread:
    return QueueRenderThread()


@pytest.fixture
def screen_bridge(screen_render_thread: QueueRenderThread) -> Bridge:
    return Bridge(screen_render_thread, answer_timeout=ANSWER_TIMEOUT_SECONDS)


@pytest.fixture
def screen_boundaries(
    output_device: OutputDevice,
    monkeypatch: pytest.MonkeyPatch,
) -> Boundaries:
    """Puts the scenario's stand-ins between the application and the desktop before it starts."""
    dialogs = ScriptedFileDialogs()
    dialogs.install(monkeypatch)
    errors = ErrorRecords()
    errors.install()
    spawns = SpawnGuard()
    spawns.install()
    provide_output_device(
        output_device,
        home=Path.home(),
        monkeypatch=monkeypatch,
    )
    return Boundaries(
        dialogs=dialogs,
        errors=errors,
        spawns=spawns,
    )


@pytest.fixture
def screen_application(
    startup: Startup,
    screen_render_thread: QueueRenderThread,
    screen_bridge: Bridge,
    screen_boundaries: Boundaries,
) -> ScreenApplication:
    """SampleToNES as ``sampletones open`` starts it, on the scenario's display and in its home."""
    profile = UserProfile.user()
    _seed_viewport(profile.state)
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
    yield Screen(
        bridge=screen_bridge,
        render_thread=screen_render_thread,
        hand=Hand(screen_bridge, device),
        language=screen_application.language,
        shortcuts=screen_application.shortcuts,
        dialogs=screen_boundaries.dialogs,
        artifacts=Path(os.environ[ARTIFACTS_VARIABLE]),
    )
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


def _seed_viewport(state_path: Path) -> None:
    """Writes the session state a first run of the scenario finds: the window filling the display."""
    state = ApplicationState(
        viewport=ViewportState(
            width=SCREEN_SIZE.width,
            height=SCREEN_SIZE.height,
            x=0,
            y=0,
        )
    )
    state_path.parent.mkdir(parents=True, exist_ok=True)
    save_yaml_atomic(state_path, state.model_dump(mode="json"))
