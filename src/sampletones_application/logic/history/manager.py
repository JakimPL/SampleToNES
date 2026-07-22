from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime
from typing import Iterator, List, Optional, Tuple

from sampletones_application.logic.project.controller import ProjectController
from sampletones_application.view_model.shared.history import HistoryDetail
from sampletones_shared.types.callback import VoidCallback
from sampletones_shared.utils.callbacks import CallbackMixin
from sampletones_shared.utils.serialization import hash_model

from .action import HistoryAction
from .errors import HistoryIntegrityError, UntrackedMutationError
from .fingerprint import ReconstructionHashCache, fingerprint_project
from .snapshot import HistoryEntry, snapshot_project
from .transaction import CoalesceKey, PendingTransaction


class HistoryManager(CallbackMixin):
    """Records project edits as an undoable stack of whole-project snapshots.

    The live project always equals a restoration of ``entries[cursor]``. Undo and
    redo move the cursor and reinstall the snapshot there, leaving every stored
    snapshot intact, so any sequence of undos and redos that returns the cursor to
    an index reproduces that index's exact state by construction.

    Edits are grouped into one entry per gesture by wrapping coordinator intent
    methods in :meth:`transaction`; consecutive gestures on one target coalesce
    into a single entry. Completeness is enforced independently:
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
        self._hash_cache: Optional[ReconstructionHashCache] = (
            ReconstructionHashCache(reconstruction_hash=hash_model) if strict else None
        )
        self._entries: List[HistoryEntry] = []
        self._cursor: int = -1
        self._saved_cursor: Optional[int] = None
        self._pending: Optional[PendingTransaction] = None
        self._restoring: bool = False
        self._last_commit_key: Optional[Tuple[HistoryAction, CoalesceKey]] = None

        self.on_history_changed: Optional[VoidCallback] = None

    @property
    def entries(self) -> Tuple[HistoryEntry, ...]:
        return tuple(self._entries)

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
        """Aligns the stack with the project lifecycle.

        Called on project transitions (new, open, close). An open project seeds a
        fresh baseline entry — the state undo can always return to — and a clean
        session makes that baseline the save point: undoing back to it later
        reinstates the on-disk content. With every project closed the stack
        empties, so the panel reports no history. A restore driven by undo/redo
        returns early here, preserving the stack it navigates.
        """
        if self._restoring:
            return

        self._pending = None
        self._last_commit_key = None
        if self._controller.is_open:
            self._entries = [self._capture(HistoryAction.INITIAL, ())]
            self._cursor = 0
            self._saved_cursor = 0 if not self._controller.is_dirty else None
        else:
            self._entries = []
            self._cursor = -1
            self._saved_cursor = None

        self._prune_hash_cache()
        self._notify()

    def mark_saved(self) -> None:
        """Records the current cursor as the last saved state.

        Restoring this exact index later reinstates the on-disk content, so the
        session reports the document clean again.
        """
        self._saved_cursor = self._cursor

    @contextmanager
    def transaction(
        self,
        action: HistoryAction,
        *,
        detail: HistoryDetail = (),
        coalesce: Optional[CoalesceKey] = None,
    ) -> Iterator[None]:
        """Groups every mutation of one user gesture into a single history entry.

        Nested scopes coalesce into the outermost transaction, and only a gesture
        that changes the project records an entry. The commit runs on scope exit even when
        the gesture raises: the mutations that already landed are part of the live
        project, so recording them preserves the invariant that the live project
        equals a restoration of ``entries[cursor]``.

        ``coalesce`` names the gesture's target. Consecutive commits that share
        the same action and target replace the previous entry, so a continuous
        interaction — a graph drag, repeated edits of
        one cell — records a single entry whose undo restores the state before
        the first gesture of the run. Any undo, redo, or jump breaks the run.
        """
        self._begin(action, detail, coalesce)
        try:
            yield
        finally:
            self._end()

    def handle_mutation(self) -> None:
        if self._restoring:
            return

        if self._pending is not None:
            self._pending.mutations += 1
            return

        if self._strict:
            raise UntrackedMutationError(
                "A project mutation fired outside a history transaction. "
                "Wrap the originating coordinator intent in HistoryManager.transaction()."
            )

        self._commit(HistoryAction.UNTRACKED, (), coalesce=None)

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

    def _begin(
        self,
        action: HistoryAction,
        detail: HistoryDetail,
        coalesce: Optional[CoalesceKey],
    ) -> None:
        if self._pending is None:
            self._pending = PendingTransaction(action=action, detail=detail, coalesce=coalesce)
            return

        self._pending.depth += 1

    def _end(self) -> None:
        if self._pending is None:
            return

        self._pending.depth -= 1
        if self._pending.depth > 0:
            return

        pending = self._pending
        self._pending = None
        if pending.mutations > 0:
            self._commit(pending.action, pending.detail, coalesce=pending.coalesce)

    def _commit(
        self,
        action: HistoryAction,
        detail: HistoryDetail,
        *,
        coalesce: Optional[CoalesceKey],
    ) -> None:
        if self._coalesces_with_last(action, coalesce):
            self._entries[self._cursor] = self._capture(action, detail)
        else:
            if self._saved_cursor is not None and self._saved_cursor > self._cursor:
                self._saved_cursor = None

            del self._entries[self._cursor + 1 :]
            self._entries.append(self._capture(action, detail))
            self._cursor = len(self._entries) - 1
            self._enforce_budget()

        self._last_commit_key = (action, coalesce) if coalesce is not None else None
        self._prune_hash_cache()
        self._notify()

    def _coalesces_with_last(
        self,
        action: HistoryAction,
        coalesce: Optional[CoalesceKey],
    ) -> bool:
        """Decides whether the commit continues an unbroken run on one target.

        A run continues only while the previous commit carried the same action
        and target and the history has stayed on that commit since: every
        restore and reset clears the recorded key, so a state the user
        deliberately navigated to is always preserved by appending. The save
        point is likewise preserved by appending, keeping the saved snapshot
        reachable for the dirty-state comparison. The cursor check restates the
        resulting invariant — replacement only ever rewrites the top of the
        stack.
        """
        return (
            coalesce is not None
            and self._last_commit_key == (action, coalesce)
            and self._cursor == len(self._entries) - 1
            and self._cursor != self._saved_cursor
        )

    def _capture(
        self,
        action: HistoryAction,
        detail: HistoryDetail,
    ) -> HistoryEntry:
        """Snapshots the live project, fingerprinting it under strict deployment.

        Capture-time fingerprints reuse the memoized per-reconstruction hashes:
        copy-on-write keeps a reconstruction's content fixed for the object's
        lifetime, so the per-gesture cost collapses to hashing the light
        structure.
        """
        project = self._controller.project
        fingerprint = (
            fingerprint_project(project, reconstruction_hash=self._hash_cache.hash)
            if self._hash_cache is not None
            else None
        )
        return HistoryEntry(
            project=snapshot_project(project),
            action=action,
            created=datetime.now(),
            detail=detail,
            fingerprint=fingerprint,
        )

    def _enforce_budget(self) -> None:
        overflow = len(self._entries) - self._budget
        if overflow > 0:
            del self._entries[:overflow]
            self._cursor -= overflow
            if self._saved_cursor is not None:
                shifted = self._saved_cursor - overflow
                self._saved_cursor = shifted if shifted >= 0 else None

    def _restore(self) -> None:
        entry = self._entries[self._cursor]
        self._last_commit_key = None
        self._restoring = True
        try:
            self._controller.replace_project(
                snapshot_project(entry.project),
                clean=self._cursor == self._saved_cursor,
            )
        finally:
            self._restoring = False

        self._verify(entry)
        self._notify()

    def _verify(self, entry: HistoryEntry) -> None:
        """Checks the restored project against the entry's recorded fingerprint.

        Verification always hashes reconstructions fresh: an in-place mutation of
        shared state keeps the object's identity, so a memoized digest would
        reproduce the pre-mutation hash and mask exactly the divergence this
        tripwire exists to catch.
        """
        if entry.fingerprint is None:
            return

        actual = fingerprint_project(self._controller.project, reconstruction_hash=hash_model)
        if actual != entry.fingerprint:
            raise HistoryIntegrityError(
                f"Restoring history entry '{entry.action}' produced a project that "
                "diverges from the recorded snapshot."
            )

    def _prune_hash_cache(self) -> None:
        """Prunes the hash cache to the reconstructions the history still retains.

        Runs wherever snapshots are discarded — reset, redo-branch truncation,
        budget eviction, and coalescing replacement — keeping the cache bounded
        by the reconstructions still reachable from the stack or the live
        project.
        """
        if self._hash_cache is None:
            return

        projects = [entry.project for entry in self._entries]
        projects.append(self._controller.project)
        self._hash_cache.prune(projects)

    def _notify(self) -> None:
        self.call(self.on_history_changed)
