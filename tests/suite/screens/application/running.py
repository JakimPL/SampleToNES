import threading
from pathlib import Path
from typing import Final, List

import dearpygui.dearpygui as dpg

from sampletones_application.application import Application
from sampletones_application.categories.manager import LanguageManager
from sampletones_application.utils.gui.keyboard import KeyEvent
from sampletones_application.utils.gui.shortcuts.ids import ShortcutId
from sampletones_application.utils.gui.shortcuts.manager import ShortcutManager
from tests.suite.screens.application.boundaries import Boundaries
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
from tests.suite.screens.keyboard import primary_combination
from tests.suite.screens.render_thread import QueueRenderThread

EXIT_TIMEOUT_SECONDS: Final[float] = 15.0


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
        """The application's language manager, which turns a language key into the words a user reads."""
        return self._application.language_manager

    @property
    def shortcuts(self) -> ShortcutManager:
        """The application's shortcut manager, which says what keys each action has under the scheme in
        place.
        """
        return self._application.shortcut_manager

    def run(self) -> None:
        """Starts the render thread and runs the application's loop on the calling thread until the loop
        ends.
        """
        self._boundaries.spawns.arm()
        self._render_thread.start()
        try:
            self._application.run()
        finally:
            self._render_thread.stop()

    def finish(self, *, failed: bool) -> None:
        """Ends the scenario: lets go of its holds, reads the after-checks and stops the application.

        A scenario that ended well leaves through the Exit shortcut; a failed one, or a screen the
        after-checks object to, stops the loop outright after a screenshot is kept.

        Raises:
            AfterCheckError: If the application broke a promise every scenario holds it to.
        """
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
        """Reads the checks that apply once the application has stopped.

        They cover late errors, surviving threads and the session state the application writes.

        Raises:
            AfterCheckError: If an error came late, a thread outlived the exit or the session state is
                missing.
        """
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
        """Presses the Exit shortcut and says whether the application stopped within the exit's time."""
        combination = primary_combination(self._application.shortcut_manager.shortcut(ShortcutId.EXIT))
        event = KeyEvent(key=combination.key, modifiers=combination.modifiers)
        self._bridge.ask(lambda: self._application.key_router.route(event))
        return self._render_thread.wait_stopped(EXIT_TIMEOUT_SECONDS)

    def _halt(self) -> None:
        """Stops the loop outright and waits for it to end."""
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
