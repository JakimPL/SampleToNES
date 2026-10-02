import os
from pathlib import Path
from typing import Final, Generator, Iterator, Optional

import pytest

from sampletones_application.application import Application
from sampletones_application.config.profile import UserProfile
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
from tests.suite.screens.dearpygui.windows import WindowManager
from tests.suite.screens.dearpygui.xtest import XTestDevice
from tests.suite.screens.environment import (
    ARTIFACTS_VARIABLE,
    REPORT_VARIABLE,
    SCREEN_SIZE,
    ScenarioFolders,
    child_environment,
    display_backend,
)
from tests.suite.screens.holds import ConversionHold, Holds, RegenerationHold, ReleaseSignal, ScanHold
from tests.suite.screens.paths import FAILURE_SCREENSHOT, SCREENS_DIRECTORY
from tests.suite.screens.render_thread import QueueRenderThread
from tests.suite.screens.screen import Screen
from tests.suite.screens.world import World, lived_in_world

CHILD_TIMEOUT_SECONDS: Final[float] = 180.0
ANSWER_TIMEOUT_SECONDS: Final[float] = 30.0
JOIN_TIMEOUT_SECONDS: Final[float] = 30.0
REPORT_RECORDER_NAME: Final[str] = "screens-report-recorder"
CONVERSION_RELEASE_FILE: Final[str] = "release-conversion"
SCAN_RELEASE_FILE: Final[str] = "release-scan"
SCAN_ENTRY_SECONDS: Final[float] = 0.05
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
        working_directory=folders.home,
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
def world() -> World:
    """What the scenario's home holds as the application starts; a scenario overrides it to seed its own."""
    return lived_in_world()


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
def screen_holds() -> Holds:
    """The work the scenario holds under way, let go before it leaves."""
    return Holds()


@pytest.fixture
def conversion_hold(
    screen_holds: Holds,
    monkeypatch: pytest.MonkeyPatch,
) -> ConversionHold:
    """Holds every conversion the scenario starts halfway through matching, until the scenario releases it."""
    hold = ConversionHold(ReleaseSignal(Path(os.environ[ARTIFACTS_VARIABLE]) / CONVERSION_RELEASE_FILE))
    hold.install(monkeypatch)
    screen_holds.add(hold)
    return hold


@pytest.fixture
def scan_hold(
    screen_holds: Holds,
    monkeypatch: pytest.MonkeyPatch,
) -> ScanHold:
    """Holds every folder scan the scenario starts once its tree is read, until the scenario releases it."""
    hold = ScanHold(
        ReleaseSignal(Path(os.environ[ARTIFACTS_VARIABLE]) / SCAN_RELEASE_FILE),
        interval=SCAN_ENTRY_SECONDS,
    )
    hold.install(monkeypatch)
    screen_holds.add(hold)
    return hold


@pytest.fixture
def regeneration_hold(
    screen_holds: Holds,
    monkeypatch: pytest.MonkeyPatch,
) -> RegenerationHold:
    """Holds every rebuild an edit of a channel asks for, until the scenario releases it."""
    hold = RegenerationHold()
    hold.install(monkeypatch)
    screen_holds.add(hold)
    return hold


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
        holds=screen_holds,
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
