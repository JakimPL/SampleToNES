# The Keyboard and the Actions It Reaches

This document describes how a key press reaches behavior in `sampletones_application`, and how an **action** is declared and shown. An action is the one name a press, a menu item and a context item all reach one behavior by. The document governs `utils/gui/keyboard/`, `utils/gui/shortcuts/`, the schemes under `sampletones_config/keybindings/`, and the menu surfaces that print an action. Consult it when giving a panel keys of its own, adding a shortcut, or putting an action on a menu.

The design truths it realizes are principles 12 and 14 of [`architecture.md`](../architecture.md): one dispatcher owns the keyboard, and an action is declared once. This document describes the mechanism behind both.

---

## The dispatcher

DearPyGui delivers a press to every registered key handler with the same global reach. No handler can stop another handler, or ImGui itself, from also seeing it. Priority and consume semantics therefore exist only where the application builds them.

A single `KeyRouter` (`utils/gui/keyboard/`) owns the one `add_key_press_handler` for the whole application. It snapshots the modifier state once into a frozen `KeyEvent` and offers that event to registered **scopes** from the highest priority to the lowest. The first active scope whose handler returns `True` claims the press and ends the walk. This software walk is the only consume mechanism the framework leaves available.

Each keyboard consumer registers one scope through `register(handle, *, priority, active)`. `active()` reports whether the scope wants keys at this moment, and `handle(event) -> bool` acts on the press and reports whether it claimed it.

### Priorities

The application orders its scopes by priority, from highest to lowest:

| Priority | Scope | Active when | Behavior |
|----------|-------|-------------|-----------|
| `MODAL` | the open dialog's navigator | a modal dialog holds the keyboard | routes Tab/Enter/Escape to the dialog's focus ring and claims every press, so a dialog owns the keyboard exclusively while it is shown |
| `PANEL` | a sub-panel the keys are meant for | its tab is in front, its card stands open, and the sub-panel holds what the keys act on: a cursor, a row picked out, or an open audition | handles the keys its own category names and yields every combination it does not own, so a higher-reaching shortcut still wins |
| `SHORTCUT` | application shortcuts (`ShortcutManager`) | always | fires the matching shortcut while no field is being edited, or whenever the shortcut is `field_transparent` |

The router offers a panel the key ahead of the shortcut scope. A panel therefore returns `False` on any combination it does not own. The grid, for example, yields every `Ctrl`-modified press. That lets field-transparent shortcuts, such as the tab switch, reach the shortcut scope while a grid cursor is set.

### A panel scope answers on its own tab, from an open card

A cursor, a picked row and an open audition all outlive a move to another tab and a collapsed card. A panel is therefore given a predicate that reports whether its tab is the one in front. It reads the predicate, and its card's collapse, at the moment of the press, as it reads focus. The composition root resolves the tab, and the scope composes the answer into its `active`. That keeps the fact in one place and leaves the router's contract as it stands: the scope decides whether it wants the key.

A shortcut in the `SHORTCUT` scope that reaches a panel's selection asks the panel the same question. The channel keys reach the converter's picked row only while its list would take a key itself.

### Focus is pulled, not pushed

Whether a text or value field keeps a plain key for itself is one router query, `is_field_focused`. It reads the focused item from DearPyGui at the moment of the press and counts it while that item is actively being edited. Every input is covered by construction, and the router alone holds the rule.

The query resolves the focused item to the field behind it. A `dpg.group` reports the state of the widget inside it, and DearPyGui names the outermost such group as the focused item. The instruments panel's sequence input, laid out beside its copy button inside a card body group, reaches the keyboard as that group. An active group therefore answers with the field being edited below it. The query follows the one branch that reports focus, so a panel-spanning group costs a key press only the path down to its field.

**Focus is claimed per key.** A focused input keeps the keys it genuinely consumes and yields the rest. A text or number field consumes `Space` and `Shift+Space`, because space is a character it types, and `Escape`, which cancels the field. Those keys serve the field while it holds focus. A modified combination stays global and fires from anywhere, which is why playing from the shown frame works while typing. Playing from the cursor row belongs to the grid: the sequencer grid claims it while the grid itself holds the keyboard.

**Interactive widgets release the keyboard.** A selectable cell or a transport button hands focus back after its click, so the next playback key reaches the router. `Space` and `Escape` therefore stay live in the moment after any click.

### The modal stack

The router holds a LIFO stack of modal handlers. `push_modal` and `pop_modal` bracket a dialog's lifetime, and the built-in `MODAL` scope routes each press to the top of the stack. `MODAL` outranks the panel and shortcut scopes, so every scope beneath it reads the keyboard as though the application had no dialogs at all.

---

## The vocabulary

One key table (`utils/gui/keyboard/keys.py`) reads a key both ways: the name a file writes and the code a press carries. One combination type, `KeyCombination`, parses that spelling, displays it, and answers whether a press matches it.

**The combination is data and the category is code.** Which keys reach an action is the reader's to choose, and which scope answers them follows from where the action is handled. A scheme is validated as it loads: every `ShortcutId` is answered, every key name resolves, and one combination reaches one action within a category. A collision is a `SystemError` at startup, beside the layout and palette failures.

---

## Schemes

### A preference layers over the shipped scheme

`ShortcutsConfig` holds the scheme name and the per-action overrides, both written the way a keybinding file writes them, so a preference outlives the build that stored it. `ShortcutCatalog.select` answers with the default for a scheme a build stopped shipping. An override is reported and left out when it names an action this build does not have, a key the table does not have, or a combination its category already gives away. One stale entry therefore costs only itself.

A change reaches the running application through `ShortcutSource.on_bindings_changed`, the keyboard's analog of the palette switch ([`palette.md`](palette.md)). The dispatcher re-reads the keys, and the menus re-print their accelerators. Each registration names the action it fires, so a rebind has little to catch up.

### A scheme is edited through a draft

`ShortcutDraft` (`utils/gui/shortcuts/draft.py`) holds the scheme being edited together with the actions the reader has touched: the combination each was given, or nothing where it was left unbound. Only those actions reach the preference, and every other key follows the scheme beneath.

An assignment displaces. Giving an action a combination its category already answers takes the key from the holder in the same step, so every scheme a draft produces is valid. The dialog names the holder and asks before that step is taken. The dialog edits the draft, and a commit activates it, so a reader rebinding Escape, Tab or Enter keeps the keys the dialog is operated by until they are done.

### A scheme belongs to a platform; an action does not

`ShortcutId` and `ShortcutCategory` are the same on every platform. `PLATFORM_SCHEME_NAMES` (`constants/keybindings.py`) says which scheme each platform ships. A profile makes that choice once, at creation, and the stored name selects from then on. The modifier table reads every spelling on every platform, and `Modifier.SUPER` displays as the name the machine is labeled with. A scheme written for one keyboard therefore loads, validates and reads on another, and the completeness validation holds every shipped scheme to the same action set.

---

## Actions

Declaring an action takes four links, and the `shortcut-actions` check holds every one of them (see [`architecture.md`](../architecture.md) § Enforcement):

| Link | Where | What it says |
|------|-------|----------------|
| The action | `utils/gui/shortcuts/ids.py` | its name, and the category that answers it |
| Its keys | every scheme under `sampletones_config/keybindings/` | the combination that fires it, `~` where it ships unbound |
| Its call | `shell.py`: a `ShortcutBindings` field and the entry naming it in the binding map, or membership of `FAMILY_SHORTCUT_IDS` | the one call the action makes |
| Its label | a `KeybindingActionElements` member and its `en.yaml` entry | how the keybindings editor lists it |

Two kinds of action give their call differently, and the check knows both.

A **family** is an action that a whole enum parameterizes, such as an export item per format or an item per channel. It is a `Dict[Enum, ShortcutId]` in `ids.py` whose reader dispatches on the enum member. `FAMILY_SHORTCUT_IDS` names the mappings that are families, so what excuses an action from giving a call of its own is written down. `SHORTCUT_IDS_BY_NAME` answers with every action and stays outside that list.

A **panel-scope** action gives no call at all, because its key scope acts on the press itself. A `DIALOG` action is named nowhere in the editor, since a dialog is operated by the keys its category holds.

### A menu item is a view of an action

`ShortcutManager.add_menu_item(shortcut_id, ...)` is how a menu names an action. It takes both the accelerator and the call from the action and keeps the item under it, so a rebind re-prints the key already on screen. An item passes a `callback` of its own only where it carries a state to show, and that call is then the one that switches the state it shows.

### A set of actions several menus show is declared by whoever owns them

The owner writes one builder, such as `GUISequencerVoicesPanel.add_action_items` for a voice or a grid's edit surface for a cell. Each menu that shows the set decides where to print it: the panel's own row menu, the menu bar's **Edit** group through `EditSurfaceProtocol` and `EditRouter`, or the **Voice** group through the panel. Adding an action to the builder reaches every menu, and the dividers around it belong to the menu and not to the set.

### A menu whose contents follow a selection is filled when it is opened

A menu bar is built once, while what an item should say follows the cursor at the moment a reader opens the menu. `MenuSection` (`ui/elements/menu_section.py`) is the mechanism. A marker leads the menu, and the framework reports it drawn once a frame while the menu stands open. A gap in those reports marks a fresh opening and refills the section. The `MenuSection` docstring says why the marker leads.
