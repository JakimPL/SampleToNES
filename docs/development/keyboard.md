# The Keyboard and the Actions It Reaches

This document describes how a key press reaches behavior in `sampletones_application`, and how an
**action** — the one name a press, a menu item and a context item all reach one behavior by — is
declared and shown. It governs `utils/gui/keyboard/`, `utils/gui/shortcuts/`, the schemes under
`sampletones_config/keybindings/`, and the menu surfaces that print an action. Consult it when
giving a panel keys of its own, adding a shortcut, or putting an action on a menu.

The design truths it realizes are principles 12 and 14 of [`architecture.md`](architecture.md):
one dispatcher owns the keyboard, and an action is declared once. This document holds the
mechanism behind both.

---

## The dispatcher

DearPyGui delivers a press to every registered key handler with the same global reach, and gives
none of them a way to stop another — or ImGui itself — from also seeing it, so priority and consume
semantics exist only where the application builds them. A single `KeyRouter`
(`utils/gui/keyboard/`) owns the one `add_key_press_handler` for the whole application, snapshots
the modifier state once into a frozen `KeyEvent`, and offers that event to registered **scopes**
from highest priority to lowest. The first active scope whose handler returns `True` claims the
press and ends the walk; this software walk is the sole consume mechanism the framework
leaves available.

Each keyboard consumer registers one scope through `register(handle, *, priority, active)`, where
`active()` reports whether the scope wants keys at this moment and `handle(event) -> bool` acts on
the press and reports whether it claimed it.

### Priorities

Three priorities order the whole application:

| Priority | Scope | Active when | Behavior |
|----------|-------|-------------|-----------|
| `MODAL` (100) | the open dialog's navigator | a modal dialog holds the keyboard | routes Tab/Enter/Escape to the dialog's focus ring and claims every press, so a dialog owns the keyboard exclusively while it is shown |
| `PANEL` (60) | a sub-panel holding a cursor or a selection — a sequencer grid, the order list, the voices, the converter's list of gathered recordings | its tab is in front and that sub-panel holds the cursor or the row picked out | handles the keys its own category names and yields the combinations it does not own so a higher-reaching shortcut still wins |
| `SHORTCUT` (40) | application shortcuts (`ShortcutManager`) | always | fires the matching shortcut while no field is being edited, or whenever the shortcut is `field_transparent` |

The router offers a panel the key ahead of the shortcut scope, so a panel returns `False` on any
combination it does not own — the grid yields every `Ctrl`-modified press — which is what lets
field-transparent shortcuts such as `Ctrl+PgDn` / `Ctrl+PgUp` tab-switching reach the shortcut
scope while a grid cursor is set.

### A panel scope answers on its own tab

A cursor and a selection outlive a move to another tab, so a panel is given the predicate that
reports whether its tab is the one in front and reads it at the moment of the press, the way focus
is read. The composition root resolves the tab and the scope composes the answer into its `active`,
which keeps the fact in one place and leaves the router's contract — the scope decides whether it
wants the key — as it stands.

### Focus is pulled, not pushed

Whether a text or value field keeps a plain key for itself is one router query, `is_field_focused`,
that reads the focused item from DearPyGui at the moment of the press and counts it while that item
is actively being edited. Every input is covered by construction, and the router alone holds the
rule.

The query resolves the focused item to the field behind it. A `dpg.group` reports the state of the
widget inside it, and DearPyGui names the outermost such group as the focused item — the
instruments panel's sequence input, laid out beside its copy button inside a card body group,
reaches the keyboard as that group. An active group therefore answers with the field being edited
below it, found by following the one branch that reports focus, so a panel-spanning group costs a
key press only the path down to its field.

### The modal stack

The router holds a LIFO stack of modal handlers; `push_modal` / `pop_modal` bracket a dialog's
lifetime, and the built-in `MODAL` scope routes each press to the top of the stack. Since `MODAL`
outranks the panel and shortcut scopes, every scope beneath it reads the keyboard as though the
application held no dialogs at all.

Its one global handler is bound in `shell.py` once the DPG context exists, on the router the
composition root built and injected into every consumer (architecture principle 7).

---

## The vocabulary

One key table (`utils/gui/keyboard/keys.py`) reads a key both ways — the name a file writes and the
code a press carries — and one combination type, `KeyCombination`, parses that spelling, displays
it, and answers whether a press matches it.

Above them stands the one declared binding (architecture principle 12). The menu printing an
accelerator, the panel acting on a press, and the dispatcher firing the callback all read that one
entry, so each of the three shows or fires whatever the scheme currently says.

**The combination is data and the category is code.** Which keys reach an action is the reader's to
choose, while which scope answers them follows from where the action is handled. A scheme is
validated as it loads — every `ShortcutId` is answered, every key name resolves, and one
combination reaches one action within a category — and a collision is a `SystemError` at startup,
beside the layout and palette failures.

---

## Schemes

### A preference layers over the shipped scheme

`ShortcutsConfig` holds the scheme name and the per-action overrides, both written the way a
keybinding file writes them, so a preference outlives the build that stored it:
`ShortcutCatalog.select` answers with the default for a scheme a build stopped shipping, and an
override naming an action this build has none of, a key the table has none of, or a combination its
category already gives away is reported and left out, so one stale entry costs only itself.

A change reaches the running application through `ShortcutSource.on_bindings_changed` — the
keyboard's analog of the palette switch ([`palette.md`](palette.md)) — and the dispatcher
re-reads the keys while the menus re-print their accelerators. Each registration names the action it
fires, which is what leaves a rebind that little to catch up.

### A scheme is edited through a draft

`ShortcutDraft` (`utils/gui/shortcuts/draft.py`) holds the scheme being edited together with the
actions the reader has touched — the combination each was given, or nothing where it was left
unbound — so what reaches the preference is those actions alone while every other key follows the
scheme beneath.

An assignment displaces: giving an action a combination its category already answers takes the key
from the holder in the same step, which is what makes every scheme a draft produces a valid one,
and the dialog names the holder and asks before that step is taken. The draft is what the dialog
edits, and a commit is what activates it, so a reader rebinding Escape, Tab or Enter keeps the keys
the dialog is operated by until they are done.

### A scheme belongs to a platform; an action does not

`ShortcutId` and `ShortcutCategory` are the same on every platform, and `PLATFORM_SCHEME_NAMES`
(`constants/keybindings.py`) states which scheme each one ships — the choice a profile makes once,
at creation, after which the stored name selects. The modifier table reads every spelling on every
platform while `Modifier.SUPER` displays as the name the machine is labeled with, so a scheme
written for one keyboard loads, validates and reads on another, and the completeness validation
holds every shipped scheme to the same action set.

---

## Actions

Declaring an action is a chain of four links, and the `shortcut-actions` check holds every one of
them (see [`architecture.md`](architecture.md) § Enforcement):

| Link | Where | What it states |
|------|-------|----------------|
| The action | `utils/gui/shortcuts/ids.py` | its name, and the category that answers it |
| Its keys | every scheme under `sampletones_config/keybindings/` | the combination that fires it, `~` where it ships unbound |
| Its call | `shell.py` — a `ShortcutBindings` field and the entry naming it in the binding map, or membership of `FAMILY_SHORTCUT_IDS` | the one call the action makes |
| Its label | a `KeybindingActionElements` member and its `en.yaml` entry | how the keybindings editor lists it |

Two kinds of action state their call differently, and the check knows both.

A **family** is an action a whole enum parameterizes — an export item per format, an item per
channel: a `Dict[Enum, ShortcutId]` in `ids.py` whose reader dispatches on the enum member.
`FAMILY_SHORTCUT_IDS` names the mappings that are families, so what excuses an action from stating
a call of its own is written down. `SHORTCUT_IDS_BY_NAME` answers with every action and stands
outside that list.

A **panel-scope** action states no call at all, because its key scope acts on the press itself. A
`DIALOG` action is named nowhere in the editor, since a dialog is operated by the keys its category
holds.

### A menu item is a view of an action

`ShortcutManager.add_menu_item(shortcut_id, ...)` is how a menu names an action: it takes both the
accelerator and the call from the action, and keeps the item under it, so a rebind re-prints the key
already on screen. An item passes a `callback` of its own only where it carries a state to show, and
then that call is the one switching the state it shows.

### A set of actions several menus show is declared by whoever owns them

The owner states one builder — `GUISequencerVoicesPanel.add_action_items` for a voice, a grid's edit
surface for a cell — and each door decides where to print it: the panel's own row menu, the menu
bar's **Edit** group through `EditSurfaceProtocol` and `EditRouter`, the **Voice** group through the
panel. Adding an action to the builder reaches every door, and the dividers around it belong to the
door rather than to the set.

### A menu whose contents follow a selection states them when it is opened

A menu bar is built once, while what an item should say follows the cursor at the moment a reader
opens the menu. `ui/elements/menu_section.py::MenuSection` is that mechanism: a marker leads the
menu, the framework reports it drawn once a frame while the menu stands open, and a gap in those
reports marks a fresh opening and restates the section. `MenuSection` states why the marker leads.
