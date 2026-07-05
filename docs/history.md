# History & Undo

This document describes the undo/redo subsystem of `sampletones_application`. The engine lives in `logic/history/` and is owned by `HistoryManager`; coordinators integrate with it as described in `docs/architecture.md`. Undo/redo is session-scoped and upholds two invariants:

1. **Completeness** — every mutation of project state belongs to the history.
2. **Reversibility determinism** — any composition of undos and redos that returns
   the cursor to an index reproduces that index's exact state.

## Engine: snapshot + cursor

`HistoryManager` holds an ordered list of whole-project snapshots and a cursor;
the live project always equals a restoration of `entries[cursor]`. Undo and redo
move the cursor and reinstall the snapshot there — they never mutate a stored
snapshot, so reversibility determinism holds by construction. Restore installs a
fresh copy through `ProjectController.replace_project`, which fires
`on_project_replaced` to rebuild the tabs exactly as loading a project does.

A snapshot (`snapshot_project`) deep-copies the light structure (song, settings,
metadata, sample shells) but **shares each `Reconstruction` by reference**.
Reconstruction edits are copy-on-write: `RegenerationService` emits a *new*
reconstruction and the apply path installs it via
`ProjectController.replace_sample_reconstruction`, so a shared reconstruction
never mutates in place and snapshots never duplicate the multi-megabyte audio
arrays. Producing the fresh reconstruction deep-copies the edited one once, on
the regeneration worker's background thread.

## Grouping vs. detection

- **Grouping — coordinators.** Each state-changing coordinator intent runs inside
  `HistoryManager.transaction(HistoryAction.X)` (the sequencer wraps its hooks via
  `_undoable`). All controller calls a gesture makes collapse into one entry;
  nested transactions coalesce. A transaction may also carry a *coalesce key*
  naming the gesture's target (a grid cell, a sample, a module setting):
  consecutive commits sharing the same action and key replace the top entry
  instead of appending, so a continuous interaction — a graph drag, repeated
  edits of one cell — records a single entry. Any undo, redo, or jump breaks
  the run, so a state the user navigated to is always preserved.
- **Detection — the controller.** `ProjectController._touch()` fires `on_mutation`
  on every fine-grained mutation. `HistoryManager.handle_mutation` counts those
  inside a transaction and rejects any that occur outside one: under strict
  deployment it raises `UntrackedMutationError`; otherwise it self-heals by
  recording the mutation as its own entry. This makes completeness a checkable
  property. Under strict deployment each committed snapshot also carries a
  fingerprint, and every restore verifies the reproduced project matches it.
  Capture-time fingerprints memoize each reconstruction's hash by object
  identity (copy-on-write keeps the content fixed for the object's lifetime),
  collapsing the per-gesture cost to the light structure; restore-time
  verification always hashes fresh, so an in-place mutation of shared state is
  caught rather than masked by the memo.

## Save point and lifecycle

The manager records the cursor of the last successful save (wired from
`ProjectController.on_saved`); a restore that lands exactly on that index
reinstates the on-disk content, so the session reports the document clean
again. A commit that truncates the saved entry away — or budget eviction that
drops it — invalidates the save point, and the session stays dirty until the
next save. Coalescing always preserves the saved entry by appending. The stack
follows the project lifecycle: an open project seeds a baseline entry, and
closing every project empties the stack, so the panel reports no history.

## History detail rendering

Committed entries are language-independent. An entry stores its action as a
`HistoryAction` enum member and its detail as data segments; language-managed
words inside a detail (e.g. a loop's on/off state) are stored as
`HistoryDetailWordSegment` keys. Action labels and word segments alike resolve
through `LanguageManager` when the history view model is built, so switching
the language re-renders past entries correctly.

## Configuration

The entry budget is a persisted user preference
(`ApplicationConfig.history.budget`, default 500, lower bound 1). Strict
checking and log level are deployment knobs
(`behavior/deployment.yaml` → `DeploymentConfig`); the deployment model is
authoritative from YAML with no field defaults. The history panel renders a
window of `layout.sequencer.history.max_rendered_entries` rows around the
cursor and repaints rows in place via an index-keyed diff.

Standalone reconstruction documents (a reconstruction loaded from disk that is not
a project sample) will gain their own history later, reusing the same engine.
