import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Final, List, Optional

import dearpygui.dearpygui as dpg

from sampletones_application.application import Application
from sampletones_application.categories.manager import LanguageManager
from sampletones_application.utils.gui.keyboard import KeyEvent
from sampletones_application.utils.gui.shortcuts.ids import ShortcutId
from sampletones_application.utils.gui.shortcuts.manager import ShortcutManager
from tests.suite.screens.boundaries.dialogs import ScriptedFileDialogs
from tests.suite.screens.boundaries.errors import ErrorRecords
from tests.suite.screens.boundaries.highlights import TableHighlights
from tests.suite.screens.boundaries.reveals import FileManagerStandIn
from tests.suite.screens.boundaries.spawns import SpawnGuard
from tests.suite.screens.checks import (
    AfterCheckError,
    contained_findings,
    quiet_findings,
    read_screen_state,
    screen_findings,
    surviving_thread_findings,
)
from tests.suite.screens.dearpygui.bridge import Bridge, RenderThreadStoppedError
from tests.suite.screens.dearpygui.hosting import SCENARIO_THREAD_NAME
from tests.suite.screens.dearpygui.screenshot import capture
from tests.suite.screens.holds import Holds
from tests.suite.screens.keyboard import primary_combination
from tests.suite.screens.render_thread import QueueRenderThread

EXIT_TIMEOUT_SECONDS: Final[float] = 15.0


@dataclass(frozen=True)
class Startup:
    """The documents a scenario's application opens as it starts, as ``sampletones open`` hands them over.

    Attributes:
        reconstruction: The reconstruction open on the Reconstructions tab, if any.
        project: The project open in the Sequencer, if any.
    """

    reconstruction: Optional[Path]
    project: Optional[Path]


NOTHING_TO_OPEN: Final[Startup] = Startup(
    reconstruction=None,
    project=None,
)


@dataclass(frozen=True)
class Boundaries:
    """What stands between a scenario's application and the desktop around it."""

    dialogs: ScriptedFileDialogs
    errors: ErrorRecords
    spawns: SpawnGuard
    holds: Holds
    file_manager: FileManagerStandIn
    highlights: TableHighlights


class ScreenApplication:
    """SampleToNES running for one scenario: its loop on the main thread, its ending read by the after-checks.

    A scenario that ends well leaves through the Exit shortcut, so every question the application asks
    about unsaved work runs as it would for a user, and the application must then stop at once. A
    scenario that failed, or a screen the after-checks object to, stops the loop outright once a
    screenshot of it is kept. Either way, the work the scenario held is let go first.
    """

    def __init__(
        self,
        application: Application,
        *,
        render_thread: QueueRenderThread,
        bridge: Bridge,
        boundaries: Boundaries,
        failure_screenshot: Path,
        state_path: Path,
    ) -> None:
        self._application = application
        self._render_thread = render_thread
        self._bridge = bridge
        self._boundaries = boundaries
        self._failure_screenshot = failure_screenshot
        self._state_path = state_path
        self._reported_errors = 0

    @property
    def language(self) -> LanguageManager:
        return self._application.language_manager

    @property
    def shortcuts(self) -> ShortcutManager:
        return self._application.shortcut_manager

    def run(self) -> None:
        self._boundaries.spawns.arm()
        self._render_thread.start()
        try:
            self._application.run()
        finally:
            self._render_thread.stop()

    def finish(self, *, failed: bool) -> None:
        self._boundaries.holds.release_all()
        findings = self._boundary_findings()
        if self._render_thread.is_running():
            findings.extend(self._screen_findings())
            if failed or findings:
                findings.extend(self._capture_failure())
                self._halt()
            elif not self._exit():
                findings.append("Leaving the application asked a question the scenario never answered")
                findings.extend(self._capture_failure())
                self._halt()

        if findings:
            raise AfterCheckError("\n".join(findings))

    def close(self) -> None:
        findings = quiet_findings(self._boundaries.errors, self._reported_errors, None)
        findings.extend(surviving_thread_findings(_application_threads()))
        if not self._state_path.exists():
            findings.append(f"The application stopped without writing its session state to {self._state_path}")

        if findings:
            raise AfterCheckError("\n".join(findings))

    def _boundary_findings(self) -> List[str]:
        self._reported_errors = self._boundaries.errors.count
        quiet = quiet_findings(self._boundaries.errors, 0, self._reported_errors)
        return [
            *quiet,
            *contained_findings(self._boundaries.spawns, self._boundaries.dialogs),
        ]

    def _screen_findings(self) -> List[str]:
        try:
            state = self._bridge.ask(read_screen_state)
        except RenderThreadStoppedError:
            return []

        return screen_findings(state)

    def _exit(self) -> bool:
        combination = primary_combination(self._application.shortcut_manager.shortcut(ShortcutId.EXIT))
        event = KeyEvent(key=combination.key, modifiers=combination.modifiers)
        self._bridge.ask(lambda: self._application.key_router.route(event))
        return self._render_thread.wait_stopped(EXIT_TIMEOUT_SECONDS)

    def _halt(self) -> None:
        try:
            self._bridge.ask(dpg.stop_dearpygui)
        except RenderThreadStoppedError:
            return

        self._render_thread.wait_stopped(EXIT_TIMEOUT_SECONDS)

    def _capture_failure(self) -> List[str]:
        try:
            capture(self._bridge, self._failure_screenshot)
        except AssertionError as error:
            return [f"The failure screenshot could not be taken: {error}"]

        return []


def _application_threads() -> List[threading.Thread]:
    """The threads running beside the main one, the scenario's own aside."""
    return [
        thread
        for thread in threading.enumerate()
        if thread is not threading.main_thread() and thread.name != SCENARIO_THREAD_NAME
    ]
