from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime
from typing import Final, Iterator, List, Optional

from sampletones_application.logic.project.controller import ProjectController
from sampletones_shared.types.callback import VoidCallback
from sampletones_shared.utils.callbacks import CallbackMixin

from .action import HistoryAction
from .errors import HistoryIntegrityError, UntrackedMutationError
from .snapshot import HistoryEntry, fingerprint_project, snapshot_project

DEFAULT_HISTORY_BUDGET: Final[int] = 500


class HistoryManager(CallbackMixin):
    """Records project edits as an undoable stack of whole-project snapshots.

    The live project always equals a restoration of ``entries[cursor]``. Undo and
    redo move the cursor and reinstall the snapshot there; they never mutate a
    stored snapshot, so any sequence of undos and redos that returns the cursor to
    an index reproduces that index's exact state by construction.

    Edits are grouped into one entry per gesture by wrapping coordinator intent
    methods in :meth:`transaction`. Completeness is enforced independently:
    :meth:`handle_mutation`, wired to the controller's ``on_mutation`` signal,
    fires on every fine-grained mutation and rejects any that occur outside a
    transaction — raising under strict deployment or self-healing otherwise.
    """

    def __init__(
        self,
        controller: ProjectController,
        *,
        budget: int,
        strict: bool,
    ) -> None:
        self._controller = controller
        self._budget = budget
        self._strict = strict
        self._entries: List[HistoryEntry] = []
        self._cursor: int = -1
        self._transaction_depth: int = 0
        self._pending_action: Optional[HistoryAction] = None
        self._pending_mutations: int = 0
        self._restoring: bool = False

        self.on_history_changed: Optional[VoidCallback] = None

    @property
    def entries(self) -> List[HistoryEntry]:
        return self._entries

    @property
    def cursor(self) -> int:
        return self._cursor

    @property
    def can_undo(self) -> bool:
        return self._cursor > 0

    @property
    def can_redo(self) -> bool:
        return self._cursor < len(self._entries) - 1

    def reset(self) -> None:
        """Discards the stack and seeds a fresh baseline from the current project.

        Called on project lifecycle transitions (new, open, close). Restores driven
        by undo/redo are excluded so they never clear the stack they navigate.
        """
        if self._restoring:
            return

        self._transaction_depth = 0
        self._pending_action = None
        self._pending_mutations = 0
        self._entries = [self._capture(HistoryAction.INITIAL)]
        self._cursor = 0
        self._notify()

    @contextmanager
    def transaction(self, action: HistoryAction) -> Iterator[None]:
        self._begin(action)
        try:
            yield
        finally:
            self._end()

    def handle_mutation(self) -> None:
        if self._restoring:
            return

        if self._transaction_depth > 0:
            self._pending_mutations += 1
            return

        if self._strict:
            raise UntrackedMutationError(
                "A project mutation fired outside a history transaction. "
                "Wrap the originating coordinator intent in HistoryManager.transaction()."
            )
        self._commit(HistoryAction.UNTRACKED)

    def undo(self) -> None:
        if not self.can_undo:
            return

        self._cursor -= 1
        self._restore()

    def redo(self) -> None:
        if not self.can_redo:
            return

        self._cursor += 1
        self._restore()

    def jump_to(self, index: int) -> None:
        if index < 0 or index >= len(self._entries) or index == self._cursor:
            return

        self._cursor = index
        self._restore()

    def _begin(self, action: HistoryAction) -> None:
        if self._transaction_depth == 0:
            self._pending_action = action
            self._pending_mutations = 0

        self._transaction_depth += 1

    def _end(self) -> None:
        self._transaction_depth -= 1
        if self._transaction_depth > 0:
            return

        action = self._pending_action
        mutated = self._pending_mutations > 0
        self._pending_action = None
        self._pending_mutations = 0
        if mutated and action is not None:
            self._commit(action)

    def _commit(self, action: HistoryAction) -> None:
        del self._entries[self._cursor + 1 :]
        self._entries.append(self._capture(action))
        self._cursor = len(self._entries) - 1
        self._enforce_budget()
        self._notify()

    def _capture(self, action: HistoryAction) -> HistoryEntry:
        project = self._controller.project
        fingerprint = fingerprint_project(project) if self._strict else None
        return HistoryEntry(
            project=snapshot_project(project),
            action=action,
            created=datetime.now(),
            fingerprint=fingerprint,
        )

    def _enforce_budget(self) -> None:
        overflow = len(self._entries) - self._budget
        if overflow > 0:
            del self._entries[:overflow]
            self._cursor -= overflow

    def _restore(self) -> None:
        entry = self._entries[self._cursor]
        self._restoring = True
        try:
            self._controller.replace_project(snapshot_project(entry.project))
        finally:
            self._restoring = False

        self._verify(entry)
        self._notify()

    def _verify(self, entry: HistoryEntry) -> None:
        if entry.fingerprint is None:
            return

        actual = fingerprint_project(self._controller.project)
        if actual != entry.fingerprint:
            raise HistoryIntegrityError(
                f"Restoring history entry '{entry.action}' produced a project that "
                "diverges from the recorded snapshot."
            )

    def _notify(self) -> None:
        self.call(self.on_history_changed)
