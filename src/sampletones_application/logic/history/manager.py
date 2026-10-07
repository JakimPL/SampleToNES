from contextlib import contextmanager
from datetime import UTC, datetime
from typing import Iterator, List, Optional, Tuple

from sampletones_application.logic.project.controller import ProjectController
from sampletones_application.logic.shared.project_source import snapshot_project
from sampletones_application.view_model.shared.history import HistoryDetail
from sampletones_shared.types.callback import VoidCallback
from sampletones_shared.utils.callbacks import CallbackMixin
from sampletones_shared.utils.hashing import hash_model

from .action import HistoryAction
from .errors import HistoryIntegrityError, UntrackedMutationError
from .fingerprint import ReconstructionHashCache, fingerprint_project
from .snapshot import HistoryEntry
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

    @property
    def is_restoring(self) -> bool:
        """Whether an undo, redo, jump or rollback is reinstalling a snapshot right now.

        Every project transition reaches its handlers through the controller's single
        ``on_project_replaced`` signal, which the composition root fans out to each tab. A
        handler that keeps session state across history navigation reads this to recognize
        it: the sequencer carries the listening mute set across it, and the Reconstructions
        tab keeps the voice it shows and redraws it as restored, while a new, opened, or
        closed document starts both fresh.
        """
        return self._restoring

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
        that changes the project records an entry. A gesture lands whole or not at
        all: one whose outermost scope ends by an exception reinstalls
        ``entries[cursor]``, the state it started from, records nothing, and lets the
        exception go on. The live project therefore equals a restoration of
        ``entries[cursor]`` whichever way the gesture ends.

        ``coalesce`` names the gesture's target. Consecutive commits that share
        the same action and target replace the previous entry, so a continuous
        interaction — a graph drag, repeated edits of
        one cell — records a single entry whose undo restores the state before
        the first gesture of the run. Any undo, redo, or jump breaks the run, and a
        rollback leaves it going, since the entry it continues stays as it was.

        What the gesture does outside the project waits on its fate through
        :meth:`after_landing`.
        """
        self._begin(action, detail, coalesce)
        completed = False
        try:
            yield
            completed = True
        finally:
            self._end(completed=completed)

    def after_landing(self, effect: VoidCallback) -> None:
        """Runs ``effect`` once the gesture in progress has landed, and at once between gestures.

        A gesture reaches beyond the project as well: a cut fills the clipboard, and a removal
        closes the voice the Reconstructions tab shows. A rollback reinstalls the project alone, so
        an effect outside it waits for the outermost scope. A gesture that completes runs its
        effects once its entry is recorded, in the order they were handed in, and one that ends by
        an exception drops them. An undo, a redo, a jump and the reinstall of a rollback run between
        gestures, so an effect they give rise to runs at once.
        """
        if self._pending is None:
            effect()
            return

        self._pending.effects.append(effect)

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
            self._pending = PendingTransaction(
                action=action,
                detail=detail,
                coalesce=coalesce,
            )
            return

        self._pending.depth += 1

    def _end(self, *, completed: bool) -> None:
        """Closes one scope; the outermost lands a completed gesture and rolls back a failed one.

        A failed gesture's effects go with it. A scope a reset ended midway has nothing left to
        close: the reset seeded the stack from the project the gesture left and let its effects go.
        """
        if self._pending is None:
            return

        self._pending.depth -= 1
        if self._pending.depth > 0:
            return

        pending = self._pending
        self._pending = None
        if completed:
            self._land(pending)
        elif pending.mutations > 0:
            self._roll_back()

    def _land(self, pending: PendingTransaction) -> None:
        """Records what a completed gesture changed, then runs what it does outside the project."""
        if pending.mutations > 0:
            self._commit(
                pending.action,
                pending.detail,
                coalesce=pending.coalesce,
            )

        for effect in pending.effects:
            effect()

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
            fingerprint_project(
                project,
                reconstruction_hash=self._hash_cache.hash,
            )
            if self._hash_cache is not None
            else None
        )
        return HistoryEntry(
            project=snapshot_project(project),
            action=action,
            created=datetime.now(UTC),
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
        self._last_commit_key = None
        self._reinstall(self._entries[self._cursor])

    def _roll_back(self) -> None:
        """Reinstalls the state a failed gesture started from, which the cursor still stands at.

        A closed project holds no state to return to.
        """
        if self._cursor < 0:
            return

        self._reinstall(self._entries[self._cursor])

    def _reinstall(self, entry: HistoryEntry) -> None:
        """Installs a fresh copy of ``entry`` as the live project and checks it against its fingerprint.

        Every handler of the replacement reads :attr:`is_restoring` while it runs, so a tab keeps
        what a history step keeps.
        """
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

        actual = fingerprint_project(
            self._controller.project,
            reconstruction_hash=hash_model,
        )
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
