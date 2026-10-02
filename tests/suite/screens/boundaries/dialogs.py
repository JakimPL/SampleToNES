import threading
from collections import deque
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Deque, Dict, List, Optional, Tuple

import pytest

import sampletones_application.utils.file_dialogs.api as file_dialogs_api
from sampletones_application.utils.file_dialogs.destination import SaveDestination, untyped_destination
from sampletones_application.utils.file_dialogs.filter import FileFilter


class DialogKind(StrEnum):
    OPEN = "open"
    SAVE = "save"
    DIRECTORY = "directory"


@dataclass(frozen=True)
class DialogRequest:
    """One file dialog the application opened during a scenario.

    Attributes:
        kind: What the dialog asked for.
        title: The title the dialog carried.
        initial_directory: The folder the dialog opened in, if the application named one.
        suggested_name: The file name a save dialog offered, if any.
        filters: The kinds of file the dialog offered to show.
        answered: Whether the scenario had queued an answer for it.
        answer: The path the dialog answered with, or ``None`` for a dismissed dialog.
    """

    kind: DialogKind
    title: str
    initial_directory: Optional[Path]
    suggested_name: Optional[str]
    filters: Tuple[FileFilter, ...]
    answered: bool
    answer: Optional[Path]


class ScriptedFileDialogs:
    """The file dialogs a scenario stands behind: each answers with what the scenario queued for its kind.

    A native dialog stops the queue the render thread drains while it stands, so a dialog here answers
    at once from the answers queued before the gesture that opens it. A dialog opening with nothing
    queued is dismissed, and the after-checks report it as a question the scenario left unanswered.
    """

    def __init__(self) -> None:
        self._answers: Dict[DialogKind, Deque[Optional[Path]]] = {kind: deque() for kind in DialogKind}
        self._requests: List[DialogRequest] = []
        self._lock = threading.Lock()

    def install(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Stands in for the native backend every file dialog of the application asks for."""
        monkeypatch.setattr(file_dialogs_api, "select_file_dialog_backend", lambda: self)

    def answer(
        self,
        kind: DialogKind,
        path: Optional[Path],
    ) -> None:
        """Queues the answer the next dialog of ``kind`` gives: ``path``, or ``None`` to dismiss it."""
        with self._lock:
            self._answers[kind].append(path)

    @property
    def requests(self) -> Tuple[DialogRequest, ...]:
        with self._lock:
            return tuple(self._requests)

    @property
    def unanswered(self) -> Tuple[DialogRequest, ...]:
        return tuple(request for request in self.requests if not request.answered)

    def open_file(
        self,
        *,
        title: str,
        initial_directory: Optional[Path],
        filters: Tuple[FileFilter, ...],
    ) -> Optional[Path]:
        return self._take(
            DialogKind.OPEN,
            title=title,
            initial_directory=initial_directory,
            suggested_name=None,
            filters=filters,
        )

    def save_file(
        self,
        *,
        title: str,
        initial_directory: Optional[Path],
        suggested_name: Optional[str],
        filters: Tuple[FileFilter, ...],
    ) -> Optional[SaveDestination]:
        answer = self._take(
            DialogKind.SAVE,
            title=title,
            initial_directory=initial_directory,
            suggested_name=suggested_name,
            filters=filters,
        )
        return untyped_destination(answer)

    def select_directory(
        self,
        *,
        title: str,
        initial_directory: Optional[Path],
    ) -> Optional[Path]:
        return self._take(
            DialogKind.DIRECTORY,
            title=title,
            initial_directory=initial_directory,
            suggested_name=None,
            filters=(),
        )

    def _take(
        self,
        kind: DialogKind,
        *,
        title: str,
        initial_directory: Optional[Path],
        suggested_name: Optional[str],
        filters: Tuple[FileFilter, ...],
    ) -> Optional[Path]:
        with self._lock:
            queued = self._answers[kind]
            answered = bool(queued)
            answer = queued.popleft() if answered else None
            self._requests.append(
                DialogRequest(
                    kind=kind,
                    title=title,
                    initial_directory=initial_directory,
                    suggested_name=suggested_name,
                    filters=filters,
                    answered=answered,
                    answer=answer,
                )
            )

        return answer
