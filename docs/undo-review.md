# Review: `undo` branch (Undo/Redo history)

**Scope.** The seven commits `991e0f18..706e7cec` on `undo`, diffed against the merge base
`5706fbc3` (the point where `undo` forked from `sequencer`): ~2,560 insertions across 54 files.
The branch introduces the snapshot-based undo/redo engine (`logic/history/`), its sequencer
wiring, the history panel, the deployment-config layer, and a refactor of the theme loader.
A separate section at the end reports how the merge with `origin/sequencer` (~23 commits:
CQT, FamiTracker export, properties dialog, test-tree reorganization) was resolved.

**Verification state.** On the merged tree: `mypy` clean (497 files), import-boundary check
clean, pre-commit clean on all touched files, full test suite **3,782 passed / 3 skipped**.

---

## 1. Overall assessment

This is a well-designed feature. The two invariants — *completeness* (every mutation belongs
to the history) and *reversibility determinism* (returning the cursor to an index reproduces
that index's state) — are stated up front, enforced mechanically rather than by convention,
and covered by behavioural tests. The design choices compose nicely:

- **Snapshot + cursor** makes reversibility hold *by construction*: undo/redo only move a
  cursor and reinstall a copy; stored snapshots are never mutated. There is no inverse-command
  bookkeeping to get wrong.
- **Completeness is checkable, not aspirational.** `ProjectController._touch()` fires
  `on_mutation` on every fine-grained mutation; `HistoryManager.handle_mutation` counts them
  inside a transaction and, under strict deployment, raises `UntrackedMutationError` for any
  mutation outside one. Strict mode turns "we forgot to wrap a gesture" from a silent
  correctness hole into an immediate crash in dev — and the merge below demonstrated the value
  of exactly this property (§7.3).
- **Copy-on-write reconstructions** keep snapshots cheap: `snapshot_project` deep-copies the
  light structure while sharing each `Reconstruction` by reference (via the `deepcopy` memo),
  and `RegenerationService` now emits a *fresh* reconstruction instead of mutating in place,
  so shared references stay valid for the life of every snapshot.
- **Fingerprint verification** under strict deployment closes the loop: if a snapshot ever
  shared mutable state with the live project, the next restore raises `HistoryIntegrityError`
  instead of silently corrupting history.

Layering is respected throughout: the engine lives in `logic/history/`, grouping decisions in
coordinators (`_undoable`), composition and cross-coordinator glue in `Application`, the panel
consumes a frozen view model through `update_view`, and shortcuts/menu go through the existing
`ShortcutManager` machinery. The architecture document was updated in the same change and
matches the implementation.

The findings below are mostly hardening, drift-prevention, and performance notes — none of
them undermines the design.

---

## 2. Correctness

### 2.1 `HistoryConfig.budget` has no lower bound — **fix before merge to `sequencer`**

`config/session/application/history.py` declares `budget: int` with only a default. A user
(or a corrupted `config.json`) can set `budget: 0` or a negative value; then
`_enforce_budget` deletes *all* entries and leaves `cursor == -1`, after which `entries[-1]`
silently aliases the last element and `can_undo`/`can_redo` misbehave. Since every persisted
config load goes through `validate_with_recovery`, a `Field(ge=1)` bound would make recovery
prune an invalid value automatically. One line buys real safety here.

### 2.2 The regeneration ordering contract is untested

`ReconstructionCoordinator._on_updated` is order-sensitive: the history hook
(`_on_reconstruction_updated`) must run *before* `apply_regenerated`, because the owning
sample is located by identity against the *prior* reconstruction object. The docstring
explains this well, but nothing pins it — a well-meaning reorder would break EDIT_RECONSTRUCTION
tracking for project samples and no test would fail. Recommend a unit test that installs a
project sample, drives `_on_regeneration_result(ServiceSuccess(...))`, and asserts both that
the sample adopted the new reconstruction and that the callback saw the old identity.

### 2.3 Inline `dpg.theme()` for selectables can resurrect the disabled-theme corruption

The branch fixed the "conflicting themes" bug properly in `ThemeLoader._mirror_disabled_entries`
(every YAML theme now carries disabled-state counterparts). But the same branch adds two *inline*
themes that bypass that machinery:

- `GUISequencerGridPanel._create_subcolumn_themes` → `_row_number_theme` (grid.py:245-253)
- `GUISequencerOrderPanel._create_entry_themes` (order.py:172-186)

Both define only an enabled-state `mvSelectable` component. Both panels are subject to
`set_enabled(False)` (project closed). If a bound selectable ever exists while its container is
disabled — even for one frame during teardown ordering — this is precisely the
"disabled item + theme lacking disabled components" trigger that corrupted the global palette
before. Today the rows/cells are torn down when the project closes, so the window is narrow,
but the safety is incidental rather than designed. Recommend either moving these to theme YAML
(mirroring is then automatic) or duplicating the entries into an `enabled: false` component.
The pre-existing subcolumn themes have the same exposure.

### 2.4 Dirty flag never clears on undo-to-save-point

`ProjectManager.install` always calls `mark_updated()`, so undoing back to the exact state of
the last save still reports unsaved changes. The docstring frames this as intended, and it is
conservative-safe (never lies about being clean). Trackers usually remember the history index
at save time and compare on restore; the snapshot engine makes that trivial (`saved_cursor`
plus an equality/fingerprint check). Worth a line in `bugs-and-todos.md` as future polish.

### 2.5 Menu Undo/Redo enablement does not track the history state

`MenuBar` enables Undo/Redo from `state.project_open` alone; the history panel's buttons are
the only UI that reflects `can_undo`/`can_redo`. Harmless (the manager no-ops), but the menu
misrepresents availability. The obstacle is structural: `on_history_changed` is a
single-listener hook and `SequencerTabCoordinator` consumes it. If the menu should follow, the
notification needs to fan out through `Application` (which already owns `_update_menu`) — see
also §3.4.

### 2.6 An exception inside a transaction commits the partial gesture

`transaction()` ends in `finally`, so a coordinator hook that raises mid-gesture still commits
whatever mutations landed. This is the *correct* choice — the live project did change, and not
committing would break `live == entries[cursor]` — but it is a deliberate semantic that
deserves a pinning test and a sentence in the `transaction` docstring.

### 2.7 Smaller items

- `HistoryManager.entries` returns the internal `List` — a consumer can mutate the stack in
  place. Returning a `Tuple[HistoryEntry, ...]` (or documenting the borrow) would match the
  immutability discipline used everywhere else.
- Detail segments are frozen at commit time, including language-manager text (`loop on/off`
  from `SequencerHistoryDetail.__init__`). Entry *labels* are resolved at render time, details
  are not; a future language switch would show mixed-language rows. Fine today, worth knowing.
- Ctrl+Z/Ctrl+Y are global and act on the project history from any tab. That is defensible
  (the project is the only document with history so far), but once standalone reconstruction
  documents gain their own history (planned per architecture.md), undo will need per-tab
  routing analogous to `PlaybackRouter`. Ctrl+Shift+Z as a redo alias is also a common
  expectation the `ShortcutManager` could register alongside Ctrl+Y.

---

## 3. Architecture & design

### 3.1 `HistoryDetailSegment` sits between two layers

The segment/role types live in `view_model/sequencer/history.py` but are *stored* inside the
logic-layer `HistoryEntry` and constructed by `SequencerHistoryDetail` (logic) and
`Application`. Per the view-model contract ("a type belongs in `view_model/` only if its sole
purpose is to feed a panel's `update_view()`"), a type persisted in domain state has outgrown
that home. Given the import matrix (logic may import view_model; view_model may not import
logic), the current placement is the only *legal* one without a new location — but two
improvements are available:

1. Move it to `view_model/shared/history.py`: it is produced by the sequencer, the
   reconstruction editor path, and (post-merge) the properties path, so the `sequencer`
   namespace is already inaccurate.
2. Longer term, treat role-tagged text segments as a domain concept in `logic/history/` and
   let the view model re-export nothing (panels already receive them through
   `HistoryEntryViewModel`).

### 3.2 `HistoryAction` ↔ `SequencerHistoryActionElements` ↔ `en.yaml` triple must not drift

Three parallel enumerations (27 members after the merge) are kept in sync by hand, and the
link is runtime-only: `SequencerHistoryActionElements(entry.action.value)` raises `ValueError`
the first time an untranslated action is *rendered*, not at startup or test time. A tiny
parity test closes this hole permanently:

```python
def test_every_history_action_has_a_label(language_manager) -> None:
    assert {member.value for member in HistoryAction} == {
        member.value for member in SequencerHistoryActionElements
    }
    for action in HistoryAction:
        language_manager[
            Page.SEQUENCER, Panel.HISTORY, TextType.LABEL,
            SequencerHistoryActionElements(action.value),
        ]
```

### 3.3 `Application._reconstruction_detail` duplicates the detail-formatting idiom

The `f"{position}:"` sample-position convention exists in `SequencerHistoryDetail._sample`
(with `colon=True`) and again inline in `application.py`. `Application` building coloured
segments by hand is also mild domain logic in the composition root. Both would be resolved by
giving the detail formatter (or a small shared helper) ownership of the reconstruction-edit
detail and letting `Application` call it.

### 3.4 Single-listener `on_history_changed`

The `CallbackMixin` single-slot pattern is the house style, and today the sequencer coordinator
is the only consumer. Note the constraint it creates: the menu (§2.5) and any future title-bar
asterisk or status indicator will need `Application` to interpose (own the hook, fan out),
which is exactly how `on_session_state_changed` already works — a consistent path exists when
needed.

### 3.5 Dead code introduced or orphaned by the branch

- `SequencerSamplesLogic.replace_sample_reconstruction` (samples.py:68-73) lost its last
  caller when the apply path moved to `Application._on_reconstruction_updated`. Per the
  "no backward compatibility for internal APIs" guideline, delete it.
- `DEFAULT_LOG_LEVEL` / `DEFAULT_STRICT_HISTORY` in `config/deployment.py` are declared but
  unused — intentionally so, since `DeploymentConfig` requires every field from YAML. Delete
  them; they contradict the model's own docstring ("declares no defaults").
- The unused `Reconstruction` import in `application.py` (already removed during the merge).

### 3.6 Points of praise worth keeping as precedents

- `_undoable` with `ParamSpec` — the detail callable mirroring the hook signature is an
  unusually clean way to attach presentation metadata to a gesture without widening any hook
  signature. The docstring says exactly what it guarantees ("a gesture that changes nothing
  records no entry").
- `PendingTransaction` bundling action/detail/depth/mutations into one object whose *presence*
  is the open-transaction signal — no boolean flag to drift (per the no-state-flags guideline).
- The `snapshot_project` memo trick (`{id(r): r}` handed to `copy.deepcopy`) is subtle but
  documented at the call site with *why it stays valid* (COW), which is the part a future
  reader needs.
- `_commit_add_reconstruction` folding the frequency adoption and the sample insertion into
  one entry, so undoing an import also restores the prior rate — good gesture-level thinking.
- The theme-loader refactor: implicit inheritance from `default` plus disabled-state mirroring
  turned a bug fix into a coherent policy ("a loaded theme fully describes both item states"),
  and it absorbed the incoming `dialog.yaml` from `sequencer` with zero migration (§7.4).

---

## 4. Performance

### 4.1 Strict-mode fingerprinting serializes audio on every commit

`_capture` under `strict_history: true` calls `fingerprint_project`, which runs
`hash_model(sample.reconstruction)` → full Pydantic JSON serialization of every reconstruction,
*including the numpy audio arrays*, on **every committed gesture** — every keystroke-level
edit in the tracker, on the UI thread. With a handful of multi-second samples this will make
dev builds noticeably heavier than production ones (the mode meant to be most used while
developing). Copy-on-write gives a free fix: a reconstruction's hash is immutable for the
lifetime of the object, so memoize `hash_model` by `id(reconstruction)` (e.g. a small
identity-keyed cache owned by the history) and the per-edit cost collapses to hashing the
light structure.

### 4.2 Every regeneration deep-copies the whole reconstruction

`RegenerationService._run` now does `reconstruction.model_copy(deep=True)` before updating one
generator — duplicating *all* generators' audio to change one. This is the honest cost of COW
and it happens on the background thread, so it is acceptable; but note the architecture doc's
"the multi-megabyte audio arrays are never duplicated for an ordinary edit" is true of
*snapshots*, not of the edit itself. A future refinement could share the untouched generators'
arrays in the copy. Worth one clarifying sentence in architecture.md.

### 4.3 The history panel rebuilds its full list on every change

`update_view` deletes and recreates the entry table each time. At the default budget of 500,
a fast editing session rebuilds up to ~500 rows × (selectable + group + N text items) per
gesture, plus the same on every undo/redo step. Options, in increasing effort: cap rendered
entries (a window around the cursor), rebuild only on structural change and re-theme rows on
cursor moves, or reuse rows in place. Fine to defer until it is felt, but it will be felt at
budget scale.

---

## 5. Tests

**What is good.** The manager tests are invariant-driven rather than implementation-driven —
`test_arbitrary_composition_reproduces_each_index` walks a mixed undo/redo/jump path while
strict fingerprint verification acts as a built-in oracle; grouping, self-healing, budget
eviction, and redo-branch truncation are all behavioural. The snapshot tests assert the two
properties that matter (independence of the light structure, shared reconstruction identity).
The detail-formatter tests read as a specification of the display language. The theme tests
are notably strong: the synthetic-YAML fixture isolates mirroring semantics, and the
loaded-set test asserts the *policy* (every theme carries the base row background) over the
real theme directory. Service tests were correctly updated to the new COW contract rather
than weakened.

**Gaps, in priority order.**

1. **Action/element/label parity** (§3.2) — cheapest, catches real future drift.
2. **Regeneration apply ordering** (§2.2) — protects a documented but unpinned contract.
3. **Production reset wiring** — the tests never wire `on_project_replaced` → `history.reset`
   the way `SequencerTabCoordinator._on_project_replaced` does, so the `_restoring` guard
   (undo must not wipe the stack it navigates) is untested in its real configuration.
4. **Nested transactions** — `depth` coalescing has no direct test.
5. **Exception inside a transaction** (§2.6) and **`jump_to` bounds** (negative, past-end,
   same-index no-op) — small, mechanical.
6. **`HistoryIntegrityError`** — the verification path never fires in any test; a test that
   deliberately mutates a stored snapshot's shared state and asserts the restore raises would
   prove the tripwire works.
7. Budget-model validation bounds once §2.1 adds them.

One style note: the test files use module-level factory helpers (`_history()`, `_controller()`,
`_formatter()`) where the guidelines prefer fixtures. `test_busy_lock.py` set this precedent,
so it is consistent house style — flagging only because the guideline says otherwise.

---

## 6. Guideline compliance notes

- Positive-phrasing documentation discipline is followed conspicuously well throughout the new
  code; docstrings explain intent and the *reason* for arbitrary choices.
- `ProjectController._touch` invokes `on_mutation` via a direct `if ... is not None` call
  instead of `CallbackMixin.call()`. This is almost certainly deliberate (`call()` logs a
  warning for every unwired invocation — one per mutation in any context without history), but
  it silently diverges from the mixin contract; a `call_silent`-style helper or a short
  docstring note would prevent someone "fixing" it back.
- `logic/history/manager.py` and `transaction.py` mix absolute and relative imports for
  siblings within the same package. Cosmetic; pick one.
- `logic/sequencer/history_detail.py` keys `_SUBCOLUMN_LETTERS`/`_SUBCOLUMN_ROLES` by raw
  strings because the `SubColumn` enum lives in `ui/panels/sequencer/input/` and logic cannot
  import it. It works (StrEnum compares equal to its value), but the type hints say `str`
  while the runtime values are `SubColumn` — the enum is a domain concept trapped in the UI
  layer, and moving it to a shared location would restore explicit typing. Pre-existing
  placement, newly felt friction.
- `deployment.yaml` ships `log_level: DEBUG`, `strict_history: true` — the *development*
  deployment. Fine while packaging is manual, but release builds need a story for swapping
  this file, and nothing currently distinguishes the two.

---

## 7. Merge of `origin/sequencer` — what was done and why

The merge is **staged but uncommitted** on `undo` (`MERGE_HEAD` present), as requested.

### 7.1 Content conflicts (2)

- `logic/project/controller.py` — both sides appended a method after `save()`: HEAD's
  `replace_project` (history restore) and sequencer's `export_module` (FTM export). Kept both;
  imports had auto-merged.
- `coordinators/sequencer.py` — HEAD wrapped the module/grid hooks in `_undoable`; sequencer
  re-stated them unwrapped and added the actions-panel wiring. Kept every `_undoable` wrapper
  and added the two new lines (`on_open_properties`, `on_export_module`) in the same block.

### 7.2 Test-tree reorganization

`origin/sequencer` moved `tests/` into `tests/unit/` + `tests/integration/`. Git auto-migrated
the *modified* files (`test_sequencer.py`, `test_reconstruction.py`, both regeneration tests —
verified the undo-side changes arrived intact) but left the *new* files behind. Relocated by
hand: `logic/history/test_manager.py`, `logic/history/test_snapshot.py`,
`ui/themes/test_loader.py` (+`__init__.py`) → `tests/unit/sampletones_application/...`, added
the missing `logic/history/__init__.py`, accepted git's suggested location for
`test_history_detail.py`, and removed the emptied old tree.

### 7.3 Real migration: the properties dialog vs. the completeness invariant

`origin/sequencer`'s `GUIProjectPropertiesWindow._commit` called `set_title` / `set_author` /
`set_comment` directly on the controller from the UI. Post-merge, under the shipped
`strict_history: true`, confirming the dialog would have raised `UntrackedMutationError`
(and in lenient mode produced three separate "Edit" entries). This is the strict mode working
as designed — it caught a feature written without history awareness. Migration applied:

- The window now exposes `on_commit: Optional[Callable[[str, str, str], None]]` and routes
  `_commit` through `CallbackMixin.call` (per the panel-hooks principle); its write path no
  longer touches the controller.
- `Application._commit_project_properties` wires the hook, wraps the three setters in one
  `HistoryAction.EDIT_PROJECT_PROPERTIES` transaction, and skips unchanged fields, so an
  untouched OK records nothing (matching the "empty gesture, no entry" semantics).
- Added the enum member, the `SequencerHistoryActionElements` mirror, and the
  `sequencer.history.label.edit_project_properties` label.
- Added `tests/unit/sampletones_application/test_project_properties_history.py` (3 tests:
  one-entry grouping, no-op confirmation, undo restores previous values) — run under strict
  history so any untracked mutation fails the test.

Note the window still *reads* through a stored `ProjectController` (in `show`/`prepare`) —
a UI→logic dependency from the sequencer side that the architecture forbids on paper. I left
reads as-is to keep the merge minimal; a follow-up could pass a small view model into `show()`.

### 7.4 Checked and found safe

- **`dialog.yaml` under the new theme-loader semantics.** Written for the old loader (no
  `extends` = standalone), it now implicitly inherits `default`. Effective appearance is
  unchanged (base + the same five overrides, identical to what global-theme stacking produced
  before) and it gains disabled mirroring for free. No migration needed.
- **`export_module`** only reads the project (`write_ftm(path, self.project)`) — no `_touch`,
  no history involvement.
- **Full-tree mutation audit** — after the merge, every `ProjectController` mutator call site
  is inside a history transaction (coordinator `_undoable` wrappers, `Application`'s two
  transaction blocks). Verified by grep across `src/`.

### 7.5 Incidental cleanup + inherited flags

- Removed the unused `Reconstruction` import in `application.py` (already unused on `undo`).
- Pylint flags two pre-existing items now visible on the merged tree, both from the sequencer
  side, listed for follow-up rather than fixed here:
  `coordinators/project.py:_export_module` catches `Exception` with a
  `# TODO: specify exception type` (explicitly named a violation in architecture.md), and
  `coordinators/sequencer.py` has a broad `except Exception` fallback in the import path that
  predates both branches.

### 7.6 Verification of the merged tree

`scripts/check_import_boundary.py` clean · `mypy` clean (497 files) · pre-commit clean on all
touched files (pylint 10.00 after the import cleanup) · full suite `uv run pytest tests/`:
**3,782 passed, 3 skipped**.

---

## 8. Recommended follow-ups (condensed)

| Priority | Item | Ref |
|----------|------|-----|
| High | `budget: Field(ge=1)` validation bound | §2.1 |
| High | Action/element/label parity test | §3.2 |
| High | Pin regeneration apply ordering with a test | §2.2 |
| Medium | Mirror or YAML-ify the inline selectable themes | §2.3 |
| Medium | Memoize reconstruction hashing under strict mode | §4.1 |
| Medium | Delete dead code (`replace_sample_reconstruction` in samples logic, unused deployment defaults) | §3.5 |
| Medium | Test: production reset wiring, nested transactions, integrity error path | §5 |
| Low | Menu undo/redo enablement via history state | §2.5 |
| Low | History panel incremental rendering / entry cap | §4.3 |
| Low | Saved-cursor dirty tracking (clean flag on undo-to-save-point) | §2.4 |
| Low | Move detail segments to `view_model/shared/` | §3.1 |
| Low | Properties window reads via view model instead of controller | §7.3 |
