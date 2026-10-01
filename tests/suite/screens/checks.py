from dataclasses import dataclass
from typing import List, Tuple

from sampletones_application.tags.general import TAG_GLOBAL_DIALOG_ERROR, TAG_GLOBAL_WINDOW_MAIN
from sampletones_application.utils.gui.modal_queue import ModalQueue, ModalQueueSnapshot
from tests.suite.screens.boundaries.dialogs import ScriptedFileDialogs
from tests.suite.screens.boundaries.errors import ErrorRecords
from tests.suite.screens.boundaries.spawns import SpawnGuard
from tests.suite.screens.dearpygui.geometry import Rect
from tests.suite.screens.dearpygui.items import WindowReading, is_tag_within, read_client_area, read_windows


class AfterCheckError(AssertionError):
    """Raised when a scenario's application broke a promise every scenario holds it to."""


@dataclass(frozen=True)
class ScreenState:
    """What the screen holds as a scenario ends: its windows, the modal line, and the client area."""

    windows: Tuple[WindowReading, ...]
    modal_line: ModalQueueSnapshot
    client_area: Rect


def read_screen_state() -> ScreenState:
    """Reads the screen as a scenario ends. Runs on the render thread."""
    return ScreenState(
        windows=read_windows(),
        modal_line=ModalQueue.snapshot(),
        client_area=read_client_area(),
    )


def quiet_findings(errors: ErrorRecords) -> List[str]:
    """The errors the application logged or let escape a thread."""
    return [f"The application reported an error: {message}" for message in errors.messages]


def contained_findings(
    spawns: SpawnGuard,
    dialogs: ScriptedFileDialogs,
) -> List[str]:
    """The programs the application tried to start, and the dialogs it opened with no answer queued."""
    return [f"The application tried to start a program: {attempt}" for attempt in spawns.refused] + [
        f"The {request.kind} file dialog '{request.title}' opened with no answer queued"
        for request in dialogs.unanswered
    ]


def screen_findings(state: ScreenState) -> List[str]:
    """What the screen still shows as a scenario ends: open conversations, error dialogs, windows off it."""
    findings: List[str] = []
    if state.modal_line.shown is not None or not state.modal_line.is_settled:
        findings.append(f"The scenario ended with a modal conversation still open: {state.modal_line}")

    for window in state.windows:
        if not window.shown or window.alias == TAG_GLOBAL_WINDOW_MAIN:
            continue
        if is_tag_within(window.alias, TAG_GLOBAL_DIALOG_ERROR):
            findings.append(f"An error dialog stands on the screen: '{window.label}'")
        if not state.client_area.contains(window.rect):
            findings.append(f"The window '{window.alias}' reaches outside the viewport: {window.rect}")

    return findings
