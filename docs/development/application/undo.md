# History & Undo

This document describes the undo/redo subsystem of `sampletones_application`. Consult it when adding a gesture that changes project state, or when changing what the history records. The engine lives in `logic/history/` and is owned by `HistoryManager`. Coordinators integrate with it as described in [`architecture.md`](../architecture.md). Undo/redo is session-scoped and upholds two invariants:

1. **Completeness.** Every mutation of project state belongs to the history.
2. **Reversibility determinism.** Any composition of undos and redos that returns the cursor to an index reproduces that index's exact state.

## Engine: snapshot + cursor

`HistoryManager` holds an ordered list of whole-project snapshots and a cursor. The live project always equals a restoration of `entries[cursor]`. Undo and redo move the cursor and reinstall the snapshot there. They leave every stored snapshot as it is, so reversibility determinism holds by construction. A restore installs a fresh copy through `ProjectController.replace_project`, which fires `on_project_replaced`. The composition root owns that signal and fans it out to the two tabs that show the project: the sequencer rebuilds its views exactly as loading a project does, and the Reconstructions tab follows the voice it shows.

## An entry owns what its gesture replaced

Each entry is a whole project, and entries share everything a gesture left alone. The project is a tree of shells over values, and `Project.snapshot` copies the shells around the values:

- A **shell** has scalars and references, and a gesture writes it in place. The shells are the project, its info and settings, the voice collection, each sample and instrument, the song with its order, and each channel's pattern pool.
- A **value** is frozen all the way down. Its sequences are tuples and its mappings are read-only. The values are a reconstruction and every part of it, a pattern and its rows, and an instrument's envelopes. The live project and every entry share them.
- A gesture puts a new value where the old one was. The new value is built from the old one and keeps the very parts the edit left alone.

An entry therefore owns the values its gesture made:

| Edited part | What the entry owns |
|---|---|
| Song cells | the edited pattern, which shares the rows the edit left alone |
| Order | the order frames |
| Pattern length | every pattern |
| Voices | the voice shells, which share their documents and envelopes |
| Instrument | its envelope set, which shares the envelopes the edit left alone |
| Reconstruction channel | the instructions and frame owners of that channel |
| Recording removal | the instructions and frame owners of each channel the removal released frames from |
| Project rate | each sample's document with its new setup, which shares the instructions |
| Settings, properties | the settings and info shells |

A reconstruction edit follows the same rule. `RegenerationService` rebuilds one channel and builds the new document around it. The apply path installs that document through `ProjectController.replace_sample_reconstruction`. An edit is recorded as it lands, in the order the reader made the edits, and an undo waits for the edits made before it ([Editing the open reconstruction](reconstruction-edits.md)).

**The types enforce the split.** A value's model is frozen, so a write in place raises where it is made. A core test walks every class a project reaches (`tests/unit/sampletones_core/project/test_values.py`). It requires each class to be a declared shell or a frozen value made of values. The history audit (`tests/suite/history/`) replays gestures against a model of the stack. After every step, it checks each stored entry against the state it recorded.

**Derived data belongs to no entry.** A document's sound is rendered from its instructions. The application keeps every render in one `RenderCache`, which the composition root builds. A render is keyed by the identity of a channel's instructions and by the setup they sound under. It goes when those instructions go, and a byte budget bounds the rest. History therefore keeps instructions only, and documents that share a channel share its render.

## The open voice across a restore

The Reconstructions tab knows the voice it shows by its id, which a snapshot and the project file both keep. A restore therefore reaches that voice the way it reaches the sequencer. A sample the restore keeps rebinds to the reconstruction the snapshot shares and redraws, and the waveform re-fits when that reconstruction runs at another NES frequency. A kept instrument redraws its envelopes. A voice the restore takes out closes, and a redo that brings it back leaves the tab empty until the reader opens it again.

Outside a restore, a change to the project only closes a voice that left it. That leaves the panel to the reader's own edit, which writes the project a moment before the open document takes it. A new, opened or closed project lets the voice go even where its id resolves, because a reopened file brings back the same ids for the project the reader has just put away.

## Grouping and detection

**Grouping happens in the coordinators.** Each state-changing coordinator intent runs inside `HistoryManager.transaction(HistoryAction.X)`. The sequencer wraps its hooks with `SequencerHistoryRecorder.undoable`, which also opens `ProjectController.batch()` inside the transaction. Every controller call a gesture makes collapses into one entry, and one gesture is one round of view notifications too. Nested transactions merge into the outermost one.

**A gesture lands whole or not at all.** A gesture whose outermost transaction ends by an exception is rolled back: the manager reinstalls `entries[cursor]`, the state the gesture started from, records nothing, and lets the exception go on to the entry point that reports it. The reinstall is the one an undo makes, so it reports itself restoring, stops song playback and rebuilds the views. A coalescing run goes on past it, since the entry the run continues stays as it was. What a gesture does outside the project waits for it to land: `HistoryManager.after_landing` runs such an effect once the outermost transaction commits, and a rollback drops it. A cut fills the clipboard this way, and the Reconstructions tab closes a removed voice this way. Between gestures, an effect runs at once.

A transaction can carry a *coalesce key* that names the gesture's target, such as a grid cell, a sample or a module setting. Consecutive commits with the same action and key replace the top entry and do not append. A continuous interaction, such as a graph drag or repeated edits of one cell, therefore records a single entry. Any undo, redo or jump ends the run, so a state the user navigated to is always preserved.

**Detection happens in the controller.** `ProjectController._touch()` fires `on_mutation` on every fine-grained mutation as it lands. A batch defers the view notifications and the dirty stamp and leaves this signal immediate, so the check below sees each mutation inside the transaction that caused it. `HistoryManager.handle_mutation` counts the mutations inside a transaction and rejects any that occur outside one. Under strict deployment it raises `UntrackedMutationError`. Otherwise it heals by recording the mutation as its own entry. This makes completeness a checkable property.

Under strict deployment each committed snapshot also carries a fingerprint, and every restore verifies that the reproduced project matches it. Capture-time fingerprints memoize each reconstruction's hash by object identity, since a reconstruction is a value and its content is fixed for the object's lifetime. That reduces the per-gesture cost to the light structure. Restore-time verification always hashes fresh, so an in-place mutation of shared state is caught and not masked by the memo.

## Save point and lifecycle

The manager records the cursor of the last successful save (wired from `ProjectController.on_saved`). A restore that lands exactly on that index reinstates the on-disk content, so the session reports the document clean again. A commit that truncates the saved entry away, or budget eviction that drops it, invalidates the save point, and the session stays dirty until the next save. Coalescing always preserves the saved entry by appending.

The stack follows the project lifecycle. An open project seeds a baseline entry, and closing every project empties the stack, so the panel reports no history.

## History detail rendering

Committed entries are language-independent. An entry stores its action as a `HistoryAction` enum member and its detail as data segments. Language-managed words inside a detail, such as a loop's on/off state, are stored as language keys in `HistoryDetailSegment` entries with a `HistoryDetailRole`. Action labels and word segments alike resolve through `LanguageManager` when the history view model is built, so switching the language re-renders past entries correctly.

## Configuration

The entry budget is a persisted user preference (`ApplicationConfig.history.budget`). The render cache's byte budget is a behavior setting (`rendering.cache_megabytes`). Strict checking and log level are deployment settings (`application/deployment.yaml` → `DeploymentConfig`), and the deployment model takes every value from the YAML with no field defaults. The history panel renders a window of rows around the cursor (`layout.sequencer.history.max_rendered_entries`) and repaints rows in place through an index-keyed diff.

**Strict checking is on where the code is written.** `deployment.yaml` has the development values, so an edit path that reaches the project outside a transaction raises `UntrackedMutationError` at once. That holds in a development run and in the test suite alike, since several tests build the whole application and read that file. A user build takes the opposite values from `scripts/runtime_hooks/release_environment.py`. A gap that reaches a release is healed into an `UNTRACKED` entry and is not shown to the user. The gap therefore surfaces where it can be fixed and stays quiet where it cannot.
