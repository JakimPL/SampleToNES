import threading
from collections import deque
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Deque, Dict, Final, List, Optional, Tuple

import pytest

import sampletones_application.utils.file_dialogs.api as file_dialogs_api
from sampletones_application.utils.file_dialogs.destination import SaveDestination
from sampletones_application.utils.file_dialogs.filter import FileFilter


class DialogKind(StrEnum):
    OPEN = "open"
    SAVE = "save"
    DIRECTORY = "directory"


UNTYPED: Final[None] = None


@dataclass(frozen=True)
class DialogAnswer:
    """What a scenario has a dialog answer: a path, and for a save dialog the file type picked in its selector.

    Attributes:
        path: The path the dialog answers with.
        type_name: The name of the offered file type the reader picks, or ``None`` to leave the selector alone.
    """

    path: Path
    type_name: Optional[str]


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
        self._answers: Dict[DialogKind, Deque[Optional[DialogAnswer]]] = {kind: deque() for kind in DialogKind}
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
            self._answers[kind].append(None if path is None else DialogAnswer(path=path, type_name=UNTYPED))

    def answer_save_as(
        self,
        path: Path,
        type_name: str,
    ) -> None:
        """Queues the answer the next save dialog gives: ``path``, with the offered type named ``type_name`` picked.

        A dialog offering no type of that name is left unanswered, which the after-checks report.
        """
        with self._lock:
            self._answers[DialogKind.SAVE].append(DialogAnswer(path=path, type_name=type_name))

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
        return _path(
            self._take(
                DialogKind.OPEN,
                title=title,
                initial_directory=initial_directory,
                suggested_name=None,
                filters=filters,
            )
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
        if answer is None:
            return None

        return SaveDestination(path=answer.path, file_type=_picked(answer, filters))

    def select_directory(
        self,
        *,
        title: str,
        initial_directory: Optional[Path],
    ) -> Optional[Path]:
        return _path(
            self._take(
                DialogKind.DIRECTORY,
                title=title,
                initial_directory=initial_directory,
                suggested_name=None,
                filters=(),
            )
        )

    def _take(
        self,
        kind: DialogKind,
        *,
        title: str,
        initial_directory: Optional[Path],
        suggested_name: Optional[str],
        filters: Tuple[FileFilter, ...],
    ) -> Optional[DialogAnswer]:
        with self._lock:
            queued = self._answers[kind]
            answered = bool(queued)
            answer = queued.popleft() if answered else None
            if answer is not None and answer.type_name is not None and not _offers(filters, answer.type_name):
                answered = False
                answer = None

            self._requests.append(
                DialogRequest(
                    kind=kind,
                    title=title,
                    initial_directory=initial_directory,
                    suggested_name=suggested_name,
                    filters=filters,
                    answered=answered,
                    answer=_path(answer),
                )
            )

        return answer


def _path(answer: Optional[DialogAnswer]) -> Optional[Path]:
    return None if answer is None else answer.path


def _offers(
    filters: Tuple[FileFilter, ...],
    type_name: str,
) -> bool:
    return any(file_filter.name == type_name for file_filter in filters)


def _picked(
    answer: DialogAnswer,
    filters: Tuple[FileFilter, ...],
) -> Optional[FileFilter]:
    """The offered type the answer picks, or ``None`` for an answer leaving the selector alone."""
    return next((file_filter for file_filter in filters if file_filter.name == answer.type_name), None)
