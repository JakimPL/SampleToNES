import os
from pathlib import Path
from typing import Final, Generator, List, Optional

import pytest

from automation.application.running import ScreenApplication
from automation.boundaries.sound_server import SoundServer
from automation.dearpygui.hosting import host
from automation.dearpygui.isolation import ReportRecorder, run_isolated
from automation.environment import (
    REPORT_VARIABLE,
    ScenarioFolders,
    child_environment,
    homes_root,
    kept_root,
    shard,
)
from automation.homes import let_go, make_worker_homes
from automation.plugin.constants import DISPLAY_KEY, HOMES_KEY, SOUND_SERVER_KEY
from automation.plugin.fixtures import _worker_display
from sampletones_shared.utils.system.system import System

CHILD_TIMEOUT_SECONDS: Final[float] = 600.0
JOIN_TIMEOUT_SECONDS: Final[float] = 30.0
REPORT_RECORDER_NAME: Final[str] = "screens-report-recorder"
SCREEN_APPLICATION_FIXTURE: Final[str] = "screen_application"
SOUND_SERVER_FOLDER: Final[str] = "sound"

__all__ = [
    "pytest_collection_modifyitems",
    "pytest_configure",
    "pytest_pyfunc_call",
    "pytest_runtest_protocol",
    "pytest_unconfigure",
]


class ScreenScenarioError(AssertionError):
    """Raised when a screen scenario is written in a shape the tier cannot host."""


def is_screen_item(item: pytest.Item) -> bool:
    """Whether ``item`` is a screen scenario, which is any function taking the application under test."""
    return isinstance(item, pytest.Function) and SCREEN_APPLICATION_FIXTURE in item.fixturenames


def is_child_process() -> bool:
    """Whether this pytest run is the fresh process one scenario runs in."""
    return REPORT_VARIABLE in os.environ


def pytest_collection_modifyitems(
    config: pytest.Config,
    items: List[pytest.Item],
) -> None:
    """Keeps this run's part of the screen scenarios, where ``SAMPLETONES_SCREENS_SHARD`` names one.

    The scenarios are counted in the order of their node ids, so every worker and every machine of a
    run spread over several splits them the same way. Items other than scenarios stay with every part.
    """
    if is_child_process():
        return

    part = shard(os.environ)
    if part is None:
        return

    scenarios = sorted(
        (item for item in items if is_screen_item(item)),
        key=lambda item: item.nodeid,
    )
    left_out = {item.nodeid for position, item in enumerate(scenarios) if not part.keeps(position)}
    deselected = [item for item in items if item.nodeid in left_out]
    items[:] = [item for item in items if item.nodeid not in left_out]
    config.hook.pytest_deselected(items=deselected)


@pytest.hookimpl(tryfirst=True)
def pytest_runtest_protocol(
    item: pytest.Item,
    nextitem: Optional[pytest.Item],
) -> Optional[bool]:
    """Runs a screen scenario in a process of its own and reports what that process reported."""
    del nextitem
    if is_child_process() or not is_screen_item(item):
        return None

    folders = ScenarioFolders.of(item.nodeid, _worker_homes(item.config), kept_root(os.environ))
    folders.prepare()
    environment = child_environment(
        os.environ,
        folders,
        display=_worker_display(item.config),
        sound_server=_worker_sound_server(item.config),
    )
    item.ihook.pytest_runtest_logstart(nodeid=item.nodeid, location=item.location)
    failed = False
    for report in run_isolated(
        item,
        environment=environment,
        working_directory=folders.home,
        report_path=folders.reports,
        timeout=CHILD_TIMEOUT_SECONDS,
    ):
        failed = failed or report.failed
        item.ihook.pytest_runtest_logreport(report=report)

    folders.finish(failed=failed)
    item.ihook.pytest_runtest_logfinish(nodeid=item.nodeid, location=item.location)
    return True


def _worker_homes(config: pytest.Config) -> Path:
    """The folder this worker's scenarios keep their homes in, made with the first of them.

    Each worker makes its own, named after its process, so runs from several checkouts at once keep
    their homes apart, and each worker's first scenario lets go of what crashed workers left.
    """
    homes = config.stash.get(HOMES_KEY, None)
    if homes is not None:
        return homes

    homes = make_worker_homes(homes_root(os.environ))
    config.stash[HOMES_KEY] = homes
    return homes


def _worker_sound_server(config: pytest.Config) -> Optional[str]:
    """The address of the PulseAudio server this worker's scenarios reach, started with the first of them.

    PortAudio carries a PulseAudio host API on Linux alone, so the server runs there, in the worker's
    homes folder, whose path stays short enough for its socket.
    """
    if System.current() is not System.LINUX:
        return None

    server = config.stash.get(SOUND_SERVER_KEY, None)
    if server is not None:
        return server.address

    server = SoundServer(_worker_homes(config) / SOUND_SERVER_FOLDER)
    address = server.start()
    config.stash[SOUND_SERVER_KEY] = server
    return address


def pytest_configure(config: pytest.Config) -> None:
    """In a scenario's own process, registers the recorder that writes its reports to the report file."""
    if is_child_process():
        recorder = ReportRecorder(config, Path(os.environ[REPORT_VARIABLE]))
        config.pluginmanager.register(recorder, REPORT_RECORDER_NAME)


def pytest_unconfigure(config: pytest.Config) -> None:
    """Stops the virtual display and the sound server this worker started, and lets its temporary homes go, if it
    made them."""
    display = config.stash.get(DISPLAY_KEY, None)
    if display is not None:
        display.stop()

    server = config.stash.get(SOUND_SERVER_KEY, None)
    if server is not None:
        server.stop()

    homes = config.stash.get(HOMES_KEY, None)
    if homes is not None:
        let_go(homes)


@pytest.hookimpl(wrapper=True)
def pytest_pyfunc_call(
    pyfuncitem: pytest.Function,
) -> Generator[None, Optional[object], Optional[object]]:
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
