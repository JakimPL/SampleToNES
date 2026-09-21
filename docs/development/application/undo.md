# History & Undo

This document describes the undo/redo subsystem of `sampletones_application`. Consult it when adding a gesture that changes project state, or when changing what the history records. The engine lives in `logic/history/` and is owned by `HistoryManager`. Coordinators integrate with it as described in [`architecture.md`](../architecture.md). Undo/redo is session-scoped and upholds two invariants:

1. **Completeness.** Every mutation of project state belongs to the history.
2. **Reversibility determinism.** Any composition of undos and redos that returns the cursor to an index reproduces that index's exact state.

## Engine: snapshot + cursor

`HistoryManager` holds an ordered list of whole-project snapshots and a cursor. The live project always equals a restoration of `entries[cursor]`. Undo and redo move the cursor and reinstall the snapshot there. They never mutate a stored snapshot, so reversibility determinism holds by construction. A restore installs a fresh copy through `ProjectController.replace_project`, which fires `on_project_replaced` to rebuild the tabs exactly as loading a project does.

A snapshot (`snapshot_project`) deep-copies the light structure (song, settings, metadata, sample shells) and **shares each `Reconstruction` by reference**. Reconstruction edits are copy-on-write. `RegenerationService` emits a *new* reconstruction, and the apply path installs it via `ProjectController.replace_sample_reconstruction`. A shared reconstruction therefore never mutates in place, and snapshots never duplicate the large audio arrays. Producing the new reconstruction deep-copies the edited one once, on the regeneration worker's background thread.

## Grouping and detection

**Grouping happens in the coordinators.** Each state-changing coordinator intent runs inside `HistoryManager.transaction(HistoryAction.X)`. The sequencer wraps its hooks with `_undoable`, which also opens `ProjectController.batch()` inside the transaction. Every controller call a gesture makes collapses into one entry, and one gesture is one round of view notifications too. Nested transactions merge into the outermost one.

A transaction can carry a *coalesce key* that names the gesture's target, such as a grid cell, a sample or a module setting. Consecutive commits with the same action and key replace the top entry and do not append. A continuous interaction, such as a graph drag or repeated edits of one cell, therefore records a single entry. Any undo, redo or jump ends the run, so a state the user navigated to is always preserved.

**Detection happens in the controller.** `ProjectController._touch()` fires `on_mutation` on every fine-grained mutation as it lands. A batch defers the view notifications and the dirty stamp and leaves this signal immediate, so the check below sees each mutation inside the transaction that caused it. `HistoryManager.handle_mutation` counts the mutations inside a transaction and rejects any that occur outside one. Under strict deployment it raises `UntrackedMutationError`. Otherwise it heals by recording the mutation as its own entry. This makes completeness a checkable property.

Under strict deployment each committed snapshot also carries a fingerprint, and every restore verifies that the reproduced project matches it. Capture-time fingerprints memoize each reconstruction's hash by object identity, since copy-on-write keeps the content fixed for the object's lifetime. That reduces the per-gesture cost to the light structure. Restore-time verification always hashes fresh, so an in-place mutation of shared state is caught and not masked by the memo.

## Save point and lifecycle

The manager records the cursor of the last successful save (wired from `ProjectController.on_saved`). A restore that lands exactly on that index reinstates the on-disk content, so the session reports the document clean again. A commit that truncates the saved entry away, or budget eviction that drops it, invalidates the save point, and the session stays dirty until the next save. Coalescing always preserves the saved entry by appending.

The stack follows the project lifecycle. An open project seeds a baseline entry, and closing every project empties the stack, so the panel reports no history.

## History detail rendering

Committed entries are language-independent. An entry stores its action as a `HistoryAction` enum member and its detail as data segments. Language-managed words inside a detail, such as a loop's on/off state, are stored as `HistoryDetailWordSegment` keys. Action labels and word segments alike resolve through `LanguageManager` when the history view model is built, so switching the language re-renders past entries correctly.

## Configuration

The entry budget is a persisted user preference (`ApplicationConfig.history.budget`). Strict checking and log level are deployment settings (`application/deployment.yaml` → `DeploymentConfig`), and the deployment model takes every value from the YAML with no field defaults. The history panel renders a window of rows around the cursor (`layout.sequencer.history.max_rendered_entries`) and repaints rows in place through an index-keyed diff.

**Strict checking is on where the code is written.** `deployment.yaml` has the development values, so an edit path that reaches the project outside a transaction raises `UntrackedMutationError` at once. That holds in a development run and in the test suite alike, since several tests build the whole application and read that file. A user build takes the opposite values from `scripts/runtime_hooks/release_environment.py`. A gap that reaches a release is healed into an `UNTRACKED` entry and is not shown to the user. The gap therefore surfaces where it can be fixed and stays quiet where it cannot.
