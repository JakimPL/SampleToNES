# Behavioral Testing

This document defines a methodology for **in-application behavioral tests**: tests that boot the real `sampletones_application`, put it into a known state, perform an action, and assert on the resulting behaviour — which controls become enabled or disabled, which dialogs appear and with what text, whether an action is permitted, and what a search or filter returns.

The goal is a **declarative, action-based test format** that lives outside Python. A maintainer writes a scenario as `given (state) → action → expect (outcome)` in YAML, and a Python runner interprets it against a booted `Application`. Scenarios read as intent and survive refactors: when the implementation moves, only the runner's action bindings change, never the scenarios.

This complements the existing test tiers rather than replacing them. Coding-level rules live in `docs/guidelines.md § Tests`; the layered contracts these tests exercise live in `docs/architecture.md`.

---

## Why a Separate Tier

The repository already has strong test infrastructure:

- **Unit tests** (`tests/unit/`) mirror ownership and assert on one narrow surface — a view model property, a coordinator branch, a service result. They bypass the heavy constructor with `object.__new__(...)` and inject `MagicMock` collaborators (see `tests/unit/sampletones_application/coordinators/test_sequencer.py`).
- **Integration tests** (`tests/integration/`) exercise real computation pipelines against synthetic data.
- **The scenario suite** (`tests/suite/scenario.py`) threads one mutable context through an ordered list of steps.

Behavioral tests fill a different niche: they assert **cross-cutting, whole-application behaviour** that emerges only when the real coordinators, logic objects, and view models are wired together by the composition root. "Adding a reconstruction while the project is closed shows a dialog and imports nothing" is a statement about the fully wired app, not about one coordinator in isolation. Unit tests prove the branch; behavioral tests prove the wiring holds it together.

They also serve a **maintainability** goal the maintainer asked for directly: a contributor who is not a Python developer can add a scenario by copying an existing YAML file and editing its verbs, states, and expectations.

---

## Part 1 — Philosophy and the Assertion Layer

### Assert on state the app already computes, not on pixels

DearPyGui renders widgets, but the *decision* about a widget's state is made one layer up and is fully observable without a GPU:

- **Enabled/disabled** is computed by a **view model** as a derived `@property` (`MenuBarViewModel.undo_enabled`, `ConverterViewModel`'s panel flags). The panel merely forwards the flag to `dpg_configure_item(tag, enabled=...)`. The truth is the view model; the DPG call is the echo.
- **Dialogs** are presented by a coordinator through the shared **`DialogsRenderer`** (`utils/gui/dialogs.py`). A coordinator resolves the text from `LanguageManager` and calls `show_info(...)`, `show_error(...)`, `show_confirmation(...)`. The decision — *which* dialog with *which* message — is a coordinator call; the window is the echo.
- **Action permission** ("can I import this reconstruction now?") is a guard inside a coordinator entry point that reads domain state (`ProjectController.is_open`) and either proceeds or presents a dialog.
- **Search/filter results** are computed by the DPG-free `Tree` model (`sampletones_core/structures/tree/tree.py`): `apply_filter(query, predicate)` populates `is_node_visible(node)`. The `show=...` flag pushed to each DPG row is the echo.

Every one of these is queryable at the layer that computes it. **Assert there.** This is what makes a scenario implementation-independent: the day a panel changes how it renders a disabled button, the view model property is untouched and the scenario still passes.

### The three assertion seams

| Behaviour to assert | Robust seam | How the runner reads it |
|---|---|---|
| Control enabled/disabled, sub-panel visible | **View model** produced by logic/application | Build the view model (`app._build_menu_bar_viewmodel()`) and read its computed `@property` |
| Dialog appeared, dialog title/message | **`DialogsRenderer`** (recording double) | Inspect the recorded `DialogRecord`s |
| Action permitted / rejected, mutation happened | **Domain state** via public controller | Read `ProjectController.is_open`, sample count, session dirty flag; check no dialog + state changed |
| Search/filter result set | **`Tree` model** | Count nodes where `tree.is_node_visible(node)` is true |

### Is DPG item state readable headlessly? Yes — but prefer the seams above

The headless boot (Part 2) calls the *real* `dpg.create_context()` and patches only the viewport/display functions. Widget-creation calls (`dpg.window`, `dpg.add_text`, `dpg.configure_item`) therefore run for real, so `dpg.does_item_exist(tag)`, `dpg.get_item_configuration(tag)["enabled"]`, and `dpg.get_value(tag)` *are* answerable. That makes DPG-level assertions technically possible and occasionally useful as a smoke check that a tag exists.

They are **not** the recommended default. A DPG assertion binds a scenario to a `TAG_*` string and to the exact widget the current UI happens to build — precisely the implementation coupling the maintainer wants to avoid. The view-model / recording-dialog / domain-state seams express the same behaviour in terms that outlive the widget tree. Reserve raw `dpg.*` queries for the rare case where the thing under test *is* the widget tree itself.

### Recording dialogs beats scraping windows

`DialogsRenderer` is constructed once in `Application.__init__` (`self.dialogs = DialogsRenderer(...)`) and injected into every coordinator as `dialogs=self.dialogs`. The existing unit tests already treat it as a boundary: they set `instance._dialogs = MagicMock()` and assert `show_info.assert_called_once()`. Behavioral tests generalise this: replace the single shared instance with a **recording double** that captures each call as a typed `DialogRecord` instead of rendering a window. One substitution covers the whole application, and assertions read the recorded intent (kind, title, message, tag, exception type) — never a `dpg` window's children.

---

## Part 2 — The Headless Boot Recipe

`tests/unit/sampletones_application/test_startup.py` already proves the app boots headless. The recipe: create a real DPG context, patch the viewport/display functions and `CallbackQueue.start`, construct `Application()`, and tear down with `stop_background_workers()` and `dpg.destroy_context()`.

Behavioral tests reuse this exactly. The list of patched functions and the boot/teardown belong in **one shared fixture** so both the startup test and the behavioral runner draw from it. Propose `tests/behavioral/boot.py`:

```python
from contextlib import ExitStack, contextmanager
from typing import Iterator, List
from unittest.mock import patch

import dearpygui.dearpygui as dpg

from sampletones_application.application import Application
from sampletones_application.utils.background import stop_background_workers

DPG_DISPLAY_FUNCTIONS: List[str] = [
    "create_context",
    "create_viewport",
    "setup_dearpygui",
    "show_viewport",
    "render_dearpygui_frame",
    "set_viewport_clear_color",
    "set_viewport_pos",
    "set_viewport_width",
    "set_viewport_height",
    "set_viewport_title",
    "set_viewport_decorated",
    "set_exit_callback",
    "set_primary_window",
]


@contextmanager
def booted_application() -> Iterator[Application]:
    """Boots a fully wired Application against a real, off-screen DPG context.

    The viewport and render calls are stubbed so no window opens, and the callback
    queue worker stays idle so the test drives frame processing itself (see
    `drain_callbacks`). Teardown mirrors `Application._exit_application`: background
    workers stop before the context is destroyed.
    """
    dpg.create_context()
    display_patches = [patch(f"dearpygui.dearpygui.{name}", return_value=None) for name in DPG_DISPLAY_FUNCTIONS]
    queue_patch = patch("sampletones_application.utils.callbacks.queue.CallbackQueue.start")
    try:
        with ExitStack() as stack:
            for active_patch in [*display_patches, queue_patch]:
                stack.enter_context(active_patch)

            yield Application()
    finally:
        stop_background_workers()
        dpg.destroy_context()
```

`test_startup.py` then imports `DPG_DISPLAY_FUNCTIONS` and `booted_application` from this module, so the patch set has a single owner. Duplicated logic gets extracted, per `docs/guidelines.md § Shared Ownership`.

### Installing the recording dialogs

`DialogsRenderer` is imported into `application.py`'s namespace, so patching `sampletones_application.application.DialogsRenderer` with a factory that returns the recording double swaps the instance the composition root builds — and therefore the instance every coordinator receives. The double records rather than renders:

```python
from enum import StrEnum
from pathlib import Path
from typing import Any, List, Optional

from pydantic import BaseModel, ConfigDict


class DialogKind(StrEnum):
    INFO = "info"
    ERROR = "error"
    CONFIRMATION = "confirmation"
    SAVE_CONFIRMATION = "save_confirmation"
    FILE_NOT_FOUND = "file_not_found"
    TEXT_INPUT = "text_input"
    MESSAGE_WITH_PATH = "message_with_path"
    RECONSTRUCTION_NOT_LOADED = "reconstruction_not_loaded"
    CONFIG_RECOVERY = "config_recovery"


class DialogRecord(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    kind: DialogKind
    title: Optional[str] = None
    message: Optional[str] = None
    tag: Optional[str] = None
    exception_type: Optional[str] = None
    path: Optional[Path] = None


class RecordingDialogsRenderer:
    """Drop-in stand-in for `DialogsRenderer` that captures presentation intent.

    It mirrors the public method surface `DialogsRenderer` exposes to coordinators and
    records each call as a `DialogRecord`. Because the whole application shares one
    dialogs instance, installing this once observes every dialog the app would raise.
    When the renderer's surface changes, this single class is the only test code to update.
    """

    def __init__(self) -> None:
        self.records: List[DialogRecord] = []

    @property
    def default_wrap(self) -> int:
        return 0

    @property
    def last(self) -> Optional[DialogRecord]:
        return self.records[-1] if self.records else None

    def show_info(self, tag: str, message: str, title: str, *, modal: bool = False) -> None:
        self.records.append(DialogRecord(kind=DialogKind.INFO, tag=tag, message=message, title=title))

    def show_error(self, exception: Exception, message: Optional[str] = None) -> None:
        self.records.append(
            DialogRecord(kind=DialogKind.ERROR, message=message, exception_type=type(exception).__name__)
        )

    def show_confirmation(self, tag: str, message: str, title: str, on_confirm: Any, **kwargs: Any) -> None:
        self.records.append(DialogRecord(kind=DialogKind.CONFIRMATION, tag=tag, message=message, title=title))

    def show_file_not_found(self, filepath: Path, message: str) -> None:
        self.records.append(DialogRecord(kind=DialogKind.FILE_NOT_FOUND, message=message, path=filepath))
```

The double implements the same method names `DialogsRenderer` presents to its callers. Any confirmation callback a scenario needs to exercise (an "Add anyway" or "Save" button) is captured in the record's kwargs, exactly as the unit tests reach `show_confirmation.call_args.kwargs["on_confirm"]` today.

### Determinism: draining the callback queue

Several actions schedule work on `CallbackQueue` with a frame `delay` — search updates (`TreeLogic.schedule_search_update`), autoplay, deferred refreshes. With `CallbackQueue.start` patched off, that worker thread never runs, which is exactly what keeps a scenario deterministic: nothing fires until the runner drives it. After an action that enqueues frame-delayed work, the runner advances frames and processes the queue synchronously:

```python
from sampletones_application.utils.callbacks.queue import CallbackQueue

_MAX_FRAMES = 8


def drain_callbacks() -> None:
    """Runs every queued callback to completion on the calling thread.

    `CallbackQueue.add` stamps each task with a target frame (`current + delay`), and
    the queue only pops a task once the frame counter reaches it. Advancing the frame
    and processing in a bounded loop flushes the delayed scheduling that search and
    autoplay rely on, keeping scenarios free of sleeps and wall-clock waits.
    """
    for _ in range(_MAX_FRAMES):
        CallbackQueue.notify_frame()
        CallbackQueue.process()
        if not CallbackQueue._callbacks:
            return
```

This turns an inherently async subsystem into a synchronous, ordered step — the property the scenario suite depends on.

---

## Part 3 — The Declarative Format

A scenario is one YAML document. Its shape:

- **`name`** — a human sentence describing the behaviour.
- **`given`** — the initial state (preconditions) the runner establishes before the first step.
- **`steps`** — an ordered list; each step has one **`action`** (a verb plus arguments) and a list of **`expect`** assertions checked immediately after the action.

An action verb and an assertion verb are the **stable vocabulary**. A scenario only ever names verbs and semantic keys; it never names a Python symbol, a `TAG_*`, or a widget. The verb's Python binding (Part 4) is where the implementation coupling is absorbed.

```yaml
name: Adding a reconstruction while the project is closed is rejected
given:
  project: closed
steps:
  - label: Import a reconstruction into the sequencer
    action:
      verb: import_reconstruction_to_sequencer
      args:
        path: fixtures/tone.stn
    expect:
      - verb: dialog_shown
        args:
          kind: info
          message_key: { page: global, panel: dialog, type: message, element: no_project_open }
      - verb: project_has_samples
        args:
          value: false
```

### Referencing dialog text by semantic key, not by wording

An `expect` never hardcodes a user-facing string. It names the **`LanguageManager` key** (page / panel / type / element), and the runner resolves it through the *same* `LanguageManager` the app used. Both sides of the comparison draw from the single source of truth described in `docs/architecture.md § principle 8`, so rewording the language file — or translating it — leaves every scenario green. A lightweight `message_contains` substring option exists for cases where only a fragment is meaningful, but the resolved-key form is the default and the most robust.

### Worked scenario (a) — action rejected, error dialog populated

The headline example. `SequencerTabCoordinator.import_reconstruction` guards on `ProjectController.is_open`; a closed project short-circuits to `show_info(TAG_GLOBAL_DIALOG_NO_PROJECT_OPEN, msg_no_project, ttl_no_project)` and imports nothing. The YAML above captures both halves: the info dialog is populated with the "no project open" message, and the sample count stays at zero.

### Worked scenario (b) — enabled/disabled transition

Undo/redo are gated by `MenuBarViewModel.undo_enabled` (`project_open and can_undo`). Closing the project must disable them regardless of history depth.

```yaml
name: Closing the project disables undo and redo in the menu
given:
  project: open
steps:
  - label: Make an undoable edit
    action:
      verb: set_project_tempo
      args: { tempo: 150 }
    expect:
      - verb: menu_flag
        args: { flag: undo_enabled, value: true }
  - label: Close the project
    action:
      verb: close_project
    expect:
      - verb: menu_flag
        args: { flag: undo_enabled, value: false }
      - verb: menu_flag
        args: { flag: redo_enabled, value: false }
      - verb: menu_flag
        args: { flag: project_open, value: false }
```

### Worked scenario (c) — search/filter result set

`TreeLogic.schedule_search_update(query)` enqueues a filter update; the `Tree` model computes visibility. The assertion counts visible leaves after the queue drains.

```yaml
name: Filtering the reconstruction browser narrows the visible files
given:
  project: open
  reconstruction_tree:
    - lead.stn
    - lead_alt.stn
    - bass.stn
steps:
  - label: Search for "lead"
    action:
      verb: search_reconstruction_browser
      args: { query: lead }
    expect:
      - verb: visible_leaf_count
        args: { equals: 2 }
  - label: Clear the search
    action:
      verb: search_reconstruction_browser
      args: { query: "" }
    expect:
      - verb: visible_leaf_count
        args: { equals: 3 }
```

### Worked scenario (d) — error dialog on an incompatible-version load

Loading a reconstruction saved by an incompatible version raises `IncompatibleReconstructionVersionError` (`sampletones_shared/exceptions/version.py`, carrying `expected_version` / `actual_version`). `ReconstructionsTabCoordinator.load_reconstruction` catches it and calls `show_error(exception, tpl_incompatible_version.format(actual, expected))`. The backward-compatibility upgrade scheme this guards is tracked in `docs/bugs-and-todos.md`.

```yaml
name: Loading an incompatible-version reconstruction shows an error dialog
given:
  project: open
steps:
  - label: Load a reconstruction stamped with an unsupported version
    action:
      verb: load_reconstruction
      args: { fixture: incompatible_version }
    expect:
      - verb: dialog_shown
        args:
          kind: error
          exception_type: IncompatibleReconstructionVersionError
```

Here the assertion pins the **exception type** carried into the dialog rather than the interpolated version numbers, so the scenario states the contract ("an incompatible version surfaces as an error dialog") without coupling to specific version strings.

---

## Part 4 — The Runner

### Validated spec models

The YAML is parsed into frozen Pydantic models, so a malformed scenario fails loudly at load time with a precise validation error rather than midway through a run.

```python
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class MessageKeySpec(BaseModel, frozen=True):
    page: str
    panel: str
    type: str
    element: str


class ActionSpec(BaseModel, frozen=True):
    verb: str
    args: Dict[str, Any] = {}


class ExpectSpec(BaseModel, frozen=True):
    verb: str
    args: Dict[str, Any] = {}


class StepSpec(BaseModel, frozen=True):
    label: str
    action: ActionSpec
    expect: List[ExpectSpec] = []


class GivenSpec(BaseModel, frozen=True):
    project: str = "closed"
    reconstruction_tree: List[str] = []


class ScenarioSpec(BaseModel, frozen=True):
    name: str
    given: GivenSpec
    steps: List[StepSpec]
```

`args` is `Dict[str, Any]` deliberately: YAML arguments are the one genuinely untyped boundary, and each verb validates its own arguments when it binds them (below). Everywhere else the models are fully typed.

### The behavioral context

The mutable context threaded through the scenario holds the booted app and the observation seams:

```python
from dataclasses import dataclass, field
from typing import Any, Dict

from sampletones_application.application import Application
from sampletones_application.categories.manager import LanguageManager


@dataclass
class BehavioralContext:
    app: Application
    dialogs: RecordingDialogsRenderer
    language: LanguageManager
    scratch: Dict[str, Any] = field(default_factory=dict)
```

### The action registry — the stable vocabulary's Python binding

A verb maps to a callable `(context, args) -> None`. This registry is the **single place implementation coupling lives**. When `import_reconstruction` moves or is renamed, one binding changes and every scenario using `import_reconstruction_to_sequencer` keeps working untouched.

```python
from pathlib import Path
from typing import Callable, Dict

ActionBinding = Callable[[BehavioralContext, Dict[str, object]], None]

ACTIONS: Dict[str, ActionBinding] = {}


def action(verb: str) -> Callable[[ActionBinding], ActionBinding]:
    def register(binding: ActionBinding) -> ActionBinding:
        ACTIONS[verb] = binding
        return binding

    return register


@action("new_project")
def _new_project(context: BehavioralContext, args: Dict[str, object]) -> None:
    context.app.project_controller.new()


@action("close_project")
def _close_project(context: BehavioralContext, args: Dict[str, object]) -> None:
    context.app.project_controller.close()


@action("set_project_tempo")
def _set_project_tempo(context: BehavioralContext, args: Dict[str, object]) -> None:
    tempo = int(args["tempo"])
    with context.app.history.transaction(HistoryAction.SET_TEMPO):
        context.app.project_controller.set_tempo(tempo)


@action("import_reconstruction_to_sequencer")
def _import_reconstruction_to_sequencer(context: BehavioralContext, args: Dict[str, object]) -> None:
    context.app._sequencer_tab.import_reconstruction(Path(str(args["path"])))


@action("search_reconstruction_browser")
def _search_reconstruction_browser(context: BehavioralContext, args: Dict[str, object]) -> None:
    panel = context.app._reconstructions_tab._browser_panel
    panel._on_search_changed(panel.tag, str(args["query"]))
    drain_callbacks()
```

Bindings reach for a coordinator's public intent method where one exists (`import_reconstruction`) and reach into a private collaborator only where the behaviour has no public entry point yet — a signal that the coordinator could grow one. Either way the reach is confined to this file, which is the whole point: scenarios never see it.

### The assertion registry

Assertion verbs map to checks against the seams. Enabled/disabled reads a view-model property through an explicit accessor table rather than dynamic attribute lookup, honouring `docs/guidelines.md`'s preference for explicit type expectations.

```python
from typing import Callable, Dict

from sampletones_application.view_model.shared.menu import MenuBarViewModel

AssertionBinding = Callable[[BehavioralContext, Dict[str, object]], None]

ASSERTIONS: Dict[str, AssertionBinding] = {}

MENU_FLAGS: Dict[str, Callable[[MenuBarViewModel], bool]] = {
    "project_open": lambda view_model: view_model.project_open,
    "reconstruction_loaded": lambda view_model: view_model.reconstruction_loaded,
    "undo_enabled": lambda view_model: view_model.undo_enabled,
    "redo_enabled": lambda view_model: view_model.redo_enabled,
}


def assertion(verb: str) -> Callable[[AssertionBinding], AssertionBinding]:
    def register(binding: AssertionBinding) -> AssertionBinding:
        ASSERTIONS[verb] = binding
        return binding

    return register


@assertion("menu_flag")
def _menu_flag(context: BehavioralContext, args: Dict[str, object]) -> None:
    view_model = context.app._build_menu_bar_viewmodel()
    read_flag = MENU_FLAGS[str(args["flag"])]
    assert read_flag(view_model) is bool(args["value"])


@assertion("dialog_shown")
def _dialog_shown(context: BehavioralContext, args: Dict[str, object]) -> None:
    record = context.dialogs.last
    assert record is not None, "expected a dialog, none was shown"
    assert record.kind == DialogKind(str(args["kind"]))

    if "message_key" in args:
        expected = resolve_message(context.language, MessageKeySpec(**args["message_key"]))
        assert record.message == expected

    if "exception_type" in args:
        assert record.exception_type == str(args["exception_type"])


@assertion("visible_leaf_count")
def _visible_leaf_count(context: BehavioralContext, args: Dict[str, object]) -> None:
    tree = context.app._reconstructions_tab._browser_logic.tree
    visible = [leaf for leaf in tree.collect_leaves() if tree.is_node_visible(leaf)]
    assert len(visible) == int(args["equals"])


@assertion("project_has_samples")
def _project_has_samples(context: BehavioralContext, args: Dict[str, object]) -> None:
    assert context.app.project_controller.has_samples is bool(args["value"])
```

`resolve_message` turns the four semantic parts into the resolved string through the same `LanguageManager` the app uses, so the comparison is wording-independent:

```python
from sampletones_application.categories.hierarchy import Page, Panel, TextType


def resolve_message(language: LanguageManager, key: MessageKeySpec) -> str:
    element = ELEMENT_FOR[(key.page, key.panel, key.element)]
    return language[Page(key.page), Panel(key.panel), TextType(key.type), element]
```

`ELEMENT_FOR` is a one-time table mapping the semantic name to the `Element` enum member for that page and panel (the enums live under `categories/elements/`). It is the only glue between the YAML's plain strings and the typed enum hierarchy, and it lives beside the registries.

### Compiling a spec into the existing scenario suite

The runner does not invent a new execution engine. A `ScenarioSpec` **compiles into** `BaseTestScenario[BehavioralContext]` from `tests/suite/scenario.py`: `build` boots the app and applies the `given`; each `StepSpec` becomes one `ScenarioStep` whose action runs the action verb and then every expect check.

```python
from tests.suite.scenario import BaseTestScenario, ScenarioStep


def compile_scenario(spec: ScenarioSpec) -> BaseTestScenario[BehavioralContext]:
    def build() -> BehavioralContext:
        context = enter_booted_context(spec)  # opens booted_application, installs recording dialogs
        apply_given(context, spec.given)
        return context

    def make_step(step: StepSpec) -> ScenarioStep[BehavioralContext]:
        def run_step(context: BehavioralContext) -> None:
            ACTIONS[step.action.verb](context, step.action.args)
            for expectation in step.expect:
                ASSERTIONS[expectation.verb](context, expectation.args)

        return ScenarioStep(label=step.label, action=run_step)

    return BaseTestScenario(
        label=spec.name,
        build=build,
        steps=[make_step(step) for step in spec.steps],
    )
```

The frozen `ScenarioStep` — `label` plus `action: Callable[[ContextT], None]` — is the natural compile target: it already threads one mutable context through ordered steps, which is exactly a `given → step → step` scenario. The suite's `run()` gives ordered execution for free.

### pytest discovery

A single parametrized test discovers every `*.scenario.yaml`, so a new file is a new test with no Python change:

```python
from pathlib import Path
from typing import List

import pytest

from sampletones_shared.utils.serialization import load_yaml

SCENARIO_ROOT = Path(__file__).parent / "scenarios"


def _discover() -> List[Path]:
    return sorted(SCENARIO_ROOT.rglob("*.scenario.yaml"))


@pytest.mark.parametrize("scenario_path", _discover(), ids=lambda path: path.stem)
def test_behavioral_scenario(scenario_path: Path) -> None:
    spec = ScenarioSpec(**load_yaml(scenario_path))
    compile_scenario(spec).run()
```

The `build` step manages the booted context through a context manager so `stop_background_workers()` and `dpg.destroy_context()` always run, even when a step assertion fails.

---

## Part 5 — Where the Files Live

Behavioral tests are cross-cutting — they exercise the whole application, not one owned unit — so they sit apart from the ownership-mirroring `tests/unit/` tree, beside `tests/integration/`:

```
tests/
├── unit/            ← mirrors src ownership; one narrow surface each
├── integration/     ← real pipelines on synthetic data
├── suite/           ← BaseTestScenario / BaseTestCase (shared, reused here)
└── behavioral/
    ├── boot.py            ← DPG_DISPLAY_FUNCTIONS + booted_application (shared with test_startup)
    ├── dialogs.py         ← RecordingDialogsRenderer + DialogRecord
    ├── context.py         ← BehavioralContext, drain_callbacks
    ├── spec.py            ← ScenarioSpec and friends (Pydantic)
    ├── actions.py         ← action registry
    ├── assertions.py      ← assertion registry + ELEMENT_FOR + resolve_message
    ├── runner.py          ← compile_scenario, apply_given, discovery test
    ├── fixtures/          ← .stn/.stp assets scenarios refer to by name
    └── scenarios/
        ├── project/*.scenario.yaml
        ├── reconstructions/*.scenario.yaml
        └── sequencer/*.scenario.yaml
```

`test_startup.py` imports its patch set from `tests/behavioral/boot.py`, retiring its private copy. `scenarios/` mirrors the app's feature areas so a maintainer finds the right folder by the tab a behaviour belongs to.

---

## Part 6 — Coverage Taxonomy and Phased Rollout

### Coverage categories

| Category | Question a scenario answers | Primary seam |
|---|---|---|
| **Enable/disable gating** | Does closing the project disable undo, redo, and the sequencer panels? Does a busy operation disable the controls that would start a competing one (architecture principle 10)? | View model |
| **Dialog population on failure** | Does an incompatible version, invalid values, deserialization error, or missing file each raise its own error dialog with the right message? | Recording dialogs |
| **Action-permission preconditions** | Is importing a reconstruction rejected with a notice while the project is closed? Does opening project properties no-op with no project? | Domain state + recording dialogs |
| **Search / filter results** | Does a query narrow the visible set to the expected count? Does clearing restore it? | `Tree` model |
| **Confirmation flows** | Does a frequency mismatch confirm before adding, and does confirming proceed while cancelling restores the field? | Recording dialogs (captured callback) |

### Phase 1 — Skeleton and proof (2 scenarios)

- Extract `tests/behavioral/boot.py` and point `test_startup.py` at it.
- Land `RecordingDialogsRenderer`, `BehavioralContext`, `drain_callbacks`, the spec models, and `compile_scenario` with the discovery test.
- Seed the action/assertion registries with just the verbs two scenarios need: **(a) import-while-closed → info dialog** and **(b) close-project → undo/redo disabled**.
- Verification: `pytest tests/behavioral` runs green; deliberately breaking the `is_open` guard turns scenario (a) red.

### Phase 2 — Vocabulary expansion

- Grow the action registry: `new_project`, `save_project`, `load_reconstruction` (from fixtures), `search_*`, tab switches, `set_*` mutations.
- Grow the assertion registry: `visible_leaf_count`, `dialog_shown` with `message_key` and `exception_type`, session dirty flag (`ProjectController.is_dirty`), sample presence (`has_samples`).
- Build the `ELEMENT_FOR` table and `resolve_message`, and the fixture set (`incompatible_version.stn`, small trees).
- Add scenarios (c) search/filter and (d) incompatible-version load.
- Verification: the four worked scenarios in this document all pass.

### Phase 3 — Broad coverage

- One scenario file per row of the taxonomy across project, reconstructions, and sequencer.
- Cover the busy-authority gating (principle 10) as enable/disable scenarios.
- Add a short contributor guide in `tests/behavioral/README` listing the available verbs and semantic keys.

### The maintainability payoff

- **Non-developers add scenarios.** A new behaviour is a new YAML file; the verbs and keys are a fixed vocabulary to compose.
- **Refactors touch the registry, not the scenarios.** Renaming or relocating a coordinator method updates one binding; every scenario using that verb is unaffected.
- **Scenarios read as intent.** `given: project closed → import → expect info dialog` is reviewable by anyone, and doubles as living documentation of the app's guard rails.

---

## Part 7 — Pitfalls

- **The callback queue worker is patched off on purpose.** Never `sleep` waiting for async work. Any action that enqueues frame-delayed callbacks (search, autoplay, deferred refresh) must call `drain_callbacks()` before its assertions, which advances frames and processes synchronously.
- **Background workers must stop.** Constructing `Application()` starts an audio device and background machinery. Teardown mirrors `Application._exit_application`: `stop_background_workers()` before `dpg.destroy_context()`. The context manager in `build` guarantees this even on a failing assertion. Skipping it risks the executor-quiescence teardown segfault recorded in `docs/bugs-and-todos.md § Architecture`.
- **Shared DPG context between scenarios.** Each scenario builds and tears down its own context so widget tags never leak across tests. Do not cache a booted app across scenarios; the isolation is worth the boot cost, which is small with rendering stubbed.
- **Modal dialogs never block.** Because the recording double captures instead of rendering, a modal confirmation returns immediately; a scenario that needs the "confirm" branch invokes the captured `on_confirm` callback explicitly, exactly as the existing sequencer unit tests do.
- **Assert on resolved keys, never on literal wording.** A scenario that hardcodes a message string breaks on the next copy edit. Name the `LanguageManager` key and let the runner resolve both sides.
- **Keep scenarios fast and focused.** One behaviour per scenario, a handful of steps. A scenario that needs a dozen steps is usually two behaviours; split it. Fixtures stay tiny (a 64-sample reconstruction is plenty).
- **When a scenario and the code disagree, find which is wrong.** Per `docs/guidelines.md § Tests`, a red scenario is evidence of a production regression until the scenario is shown to be incorrect. Do not weaken an expectation to make it pass.
