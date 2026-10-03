import os
from pathlib import Path
from typing import Final, Generator, Optional

import pytest

from tests.suite.screens.application.running import ScreenApplication
from tests.suite.screens.dearpygui.hosting import host
from tests.suite.screens.dearpygui.isolation import ReportRecorder, run_isolated
from tests.suite.screens.environment import REPORT_VARIABLE, ScenarioFolders, child_environment
from tests.suite.screens.paths import SCREENS_DIRECTORY
from tests.suite.screens.plugin.constants import DISPLAY_KEY
from tests.suite.screens.plugin.fixtures import _worker_display

CHILD_TIMEOUT_SECONDS: Final[float] = 600.0
JOIN_TIMEOUT_SECONDS: Final[float] = 30.0
REPORT_RECORDER_NAME: Final[str] = "screens-report-recorder"
SCREEN_APPLICATION_FIXTURE: Final[str] = "screen_application"


class ScreenScenarioError(AssertionError):
    """Raised when a screen scenario is written in a shape the tier cannot host."""


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
    """In a scenario's own process, registers the recorder that writes its reports to the report file."""
    if is_child_process():
        recorder = ReportRecorder(config, Path(os.environ[REPORT_VARIABLE]))
        config.pluginmanager.register(recorder, REPORT_RECORDER_NAME)


def pytest_unconfigure(config: pytest.Config) -> None:
    """Stops the virtual display this worker started, if it started one."""
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
