# The Reconstruction Browser

This document governs the tree of reconstructions the **Reconstructions** and **Sequencer** tabs
share: how a reconstructions directory becomes rows, what a row stands for, and what it answers.
Consult it when changing what the browser lists, how a row reads, or what a click on one does. It
complements `docs/development/architecture.md` (layering and ownership) and
`docs/development/guidelines.md` (coding rules).

---

## Principles

1. **One reading of the disk feeds every view.** A refresh walks the reconstructions directory once
   into a `ReconstructionScan`, and every branch is built from that record. The views therefore agree
   about what exists by construction, and a folder name is parsed into its configuration fields once
   per refresh.
2. **The model carries the shape; the panel carries the widgets.** Which rows exist, what they are
   called, which of them fold together and in what order they sit are decided on the tree. Both tabs
   render one model, so they show one shape, and each rule is exercised without a window.
3. **A row's identity is its path; its name is a label.** Favorites, the context menus, copy-path,
   playback and opening a reconstruction all key on `filepath`. That is what frees a name to be
   rewritten — a configuration directory renamed to its generator abbreviation, a chain of headings
   joined into one row, a colliding label marked with its configuration hash.
4. **The browser writes the headings the disk states rather than holds.** A frequency pair, a
   transformation, a source folder, one source audio: each becomes a row that carries no path of its
   own. What such a row offers follows from the subtree beneath it.
5. **One thing may stand in several places.** A reconstruction is listed by the configuration that
   produced it and again by the audio it was made from, so an action on the thing rather than on the
   row asks for every row standing for it (`Tree.find_nodes`, `BrowserManager.nodes_at`) and hands
   them to both tabs.
6. **Per-row work happens off the main thread.** A rebuild resolves each row into a `NodeSpec` on the
   background worker — tag, label, font, theme, handler, open state — and the main thread creates the
   widgets from those specs, spread across frames.
7. **What a browser narrows to is its own.** Both tabs render one model, so which rows a browser shows
   is decided by the panel showing it: a search typed in one tab leaves the other reading as it was,
   and each browser opens in the mode a session left it in.
8. **The reader's shape is theirs to keep.** Which rows stand open is what the reader made of the
   tree, so a browser records it and brings it back: a refresh, a change of filter and a repaint leave
   the tree standing as it was, and so does the next run of the application. What a filter unfolds on
   top of that shape is the reader's to ask for.

---

## The pipeline

`BrowserManager` (`logic/reconstruction/browser/manager.py`) owns the tree and runs a refresh in four
steps: **scan** the directory, **build** each branch from that one scan, **shape** what came out, and
**publish** it through `Tree.set_root`. `BrowserLogic` sits above it as the surface the coordinators
drive, and `get_all_reconstruction_files` reads the scan.

| Stage | Module | What it does |
|---|---|---|
| Scan | `tree/scan.py` | `scan_reconstructions` walks the directory once, recording each folder with the configuration its name states and each `.stn` file beneath it |
| Records | `tree/entries/` | `DirectoryEntry`, `ReconstructionEntry`, `ReconstructionScan` — frozen, path-only, no widgets and no tree |
| Configuration branch | `tree/configurations/` | `branch.py` lays the scanned folders out as they sit; `grouping.py` lifts a top-level configuration directory under frequency ▶ transformation groups and names it by its generators; `naming.py` gives the remaining configuration directories friendly names, unique among their siblings |
| Sample branch | `tree/samples/` | `variants.py` regroups every top-level configuration directory's reconstructions by the audio they mirror (`SampleSource` → `SampleVariant`); `branch.py` rebuilds the mirrored folders as groups and gathers each audio's variants under one sample row, each labelled by its configuration |
| Shaping | `tree/prune.py`, `tree/collapse.py`, `tree/order.py` | Run in that order over each branch, deepest rows first |
| Containers | `tree/containers.py` | `find_or_create_group` and `find_or_create_sample` extend the heading of that name a parent already holds; each node type is looked up among the siblings of its own kind, so a folder and an audio sharing a name stay two rows |

The policy the two branches share: a configuration directory sitting at the top level of the
reconstructions directory is the one lifted under groups and transposed into the sample view. A
configuration directory nested inside a plain folder keeps its friendly name where it sits, and a
reconstruction outside every configuration directory appears in the configuration branch, that being
the branch which follows the disk.

## The node vocabulary

`sampletones_core/structures/tree/` holds the nodes, all anytree-backed:

* `TreeNode(name, node_type)` — a row and its kind. `NodeType.ROOT` for the container both branches
  hang from, `GROUP` and `SAMPLE` for the headings the browser writes, `DIRECTORY` and `FILE` for what
  the disk holds.
* `FileSystemNode(filepath)` — a row standing for a path. Favorites, playability, themes and the path
  items all test for this class.
* `ConfigNode(config)` — a filesystem row belonging to a reconstruction configuration, carrying the
  parsed `ConfigDirectoryFields`. It subclasses `FileSystemNode` so every reader of a path keeps
  working, and the fields travel with the row, which is what lets a label, a tooltip and a font state
  the configuration from the node already in hand.

`create_directory_node` chooses between the last two from the fields the scan read. Which row carries
the configuration follows the branch: in the configuration branch it is the directory that names it,
and in the sample branch it is the variant leaf, since there the configuration is what distinguishes
one row from the next.

## The shaping rules

* **Prune** (`prune_empty_containers`) — a heading the browser wrote that gathers nothing leaves,
  deepest first, so a whole chain of them goes at once and a reconstructions directory with nothing to
  show stays silent. A folder the disk holds stays, since the configuration branch mirrors the disk.
* **Collapse** (`collapse_single_child_containers`) — a heading standing above a single row folds into
  that row, which takes the joined name (`DISPLAY_SEPARATOR` between levels) and rises into its place.
  The surviving row keeps its node type, path, configuration and children, so its click behaviour,
  theme, context menu and favorite star carry over. A fold that would repeat a name already beside it
  stays open instead, and the branch roots stay in place. With a single configuration present the
  configuration branch reads as one row per reconstruction, and it grows back into groups as soon as a
  second configuration arrives.
* **Order** (`order_children`) — containers ahead of leaves, then `natural_sort_key` over the label, so
  a row sits where its displayed name puts it and `8 kHz` precedes `44.1 kHz`. The pass runs once every
  label is final; the branches directly under the container root keep the order the builder states them
  in.
* **Unique sibling labels** (`unique_display_names`, `sampletones_core/configs/display.py`) — where
  siblings would read alike, every member of that label takes its short configuration hash. One rule
  serves the generator directories under a transformation group, the nested configuration directories,
  and the variants under a sample.

## The panels

The browsers form one line of inheritance, each level owning what it shares:

* `GUITreePanel` (`ui/elements/tree/tree.py`) — a tree of rows: the controls it narrows by and the filter
  they compose, the shape it holds across rebuilds, the rebuild handshake, spec collection, themes and
  fonts per row, the detail tooltip, the status-bar messages, and the context-menu items every browser
  can offer.
* `GUIFileBrowserPanel` (`ui/elements/tree/browser.py`) — a browser of files as a collapsible card: the
  controls bringing the tree up to date and folding it away, the tree window, the folder-and-file
  handler pair, and enabling the card as the tree locks and unlocks. A subclass declares its widgets as
  a `FileBrowserTags` class attribute and states what its card and refresh control read.
* `GUIReconstructionBrowserPanel` (`ui/panels/shared/browser.py`) — the reconstruction browser: the
  rows the two branches hold, the colour a group and a sample read in, and the context menus. The
  Reconstructions and Sequencer panels below it name their widgets, their refresh control, and what
  opening a reconstruction means in that tab.

The Main tab's filesystem explorer and the Instructions tab's library catalogue sit on
`GUIFileBrowserPanel` as well, so the card, the search and the rebuild machinery are shared with them.

**A rebuild** starts on the tree worker: `_launch_rebuild` takes the tree lock, brings the model up to
date, collects the rows into specs, and hands them to `TreeEmitter`, which clears the old rows and
stages the new ones in budget-sized batches so interactive callbacks run between slices. The
completion callback shows the empty state where one is called for, runs the panel's hook, and releases
the lock. Because a browser is asked to rebuild from either tab and from several places in the
application, exactly one rebuild is in flight at a time.

**A row's tag** (`compose_node_tag`, `ui/elements/tree/tag.py`) joins the names above it, which reads
the row back to whoever inspects the widget tree, and appends a digest over the exact path of
`(node_type, name)` pairs. Rows the names alone spell alike — a folder and the audio beside it, two
labels differing only in spacing or case — therefore keep tags of their own. A tag is composed rather
than stored, so any holder of a node can address its row: this is how expanding a subtree, repainting a
star and applying a filter reach the widgets.

**What a row answers** follows its kind. A reconstruction plays on a click, opens on a double click,
and offers its path items, the tab's own actions and the favorite mark. A directory offers its path
items and the favorite mark. A group or a sample stands for no path, so its menu reads the subtree: how
many reconstructions it gathers, expanding and collapsing everything below it, the label the tree shows
it by, and — on a sample — the audio its reconstructions were made from, answered through any one of
them.

**Favorites are paths.** `TreeLogic.is_node_favorite` tests the row's path against the session's set,
and `has_favorite_ancestor` tests the path's parents, so a reconstruction reads as part of a favorite
folder wherever a view puts it — including the sample branch, whose headings carry no path. Since one
path reaches the panel as several rows, `application.py` resolves the toggled path into every row
standing for it and hands them to both tabs, and each row repaints with the ancestry its own path
carries.

## Filtering

`TreeFilter` (`ui/elements/tree/filter.py`) holds what a browser is currently asked to show, and the
panel showing it owns the filter. It is stated whole and replaced whole — `with_query`,
`with_favorites_only` — so one place resolves what the browser shows, and `NO_FILTER` is the filter a
browser showing its whole tree holds.

The two criteria answer different questions, so each lands in a different place:

| Criterion | What it decides | Where it lands | What a change costs |
|---|---|---|---|
| `favorites_only` | which rows the browser **draws** | `_append_spec` records the rows the mode shows, so `TreeEmitter` creates widgets for those alone | `redraw_tree` collects the rows again from the model in hand, on the tree worker |
| `query` | which of the drawn rows are **shown** | `update_tree_visibility` flips `show` over the rows already on screen, once the typing settles | a resolution of the query, debounced |

One rule serves both. `TreeVisibility` (`sampletones_core/structures/tree/visibility.py`) takes the
rows a criterion named and answers which rows stay: a named row, a row leading down to one, and a row
one holds. `resolve_visibility` keeps the named rows and the rows above them, so what a pass holds in
memory follows the size of what was found, and a row beneath a match is answered from its own path
upwards.

**What a criterion names and what it keeps are two sets.** A criterion points the reader at some rows
and brings others along with them, and only the first kind is worth unfolding to. The rows a criterion
names are its **anchors**: for a search, the rows whose label matched; for the favorites mode, a row a
star sits on, and — where no row stands for the starred path — the shallowest rows that path reaches.
In the sample branch the headings carry no path, which is what makes the variants the rows a starred
folder arrives at.

**A criterion is read the way that criterion means.** A search shows what a matching row gathers, so a
match opens along with the rows above it (`TreeVisibility.should_expand`). The favorites mode points
the reader at a star, so the rows above it open and the star's own row stands where the reader left it
(`TreeVisibility.leads_to`) — a starred folder is revealed rather than unfolded. A starred
reconstruction inside a starred folder anchors on its own, which is what opens the folder above it.

**Which stars are followed is the reader's.** The mode decides what is drawn; whether it also unfolds
is a preference stated per kind of favorite, held in `ApplicationConfig.browser` and offered as
**View ▸ Auto-expand favorites**. A starred reconstruction reads the reconstructions answer; a starred
folder, and everything it brings in where no row stands for it, reads the directories answer. Both are
off by default, so turning the mode on narrows the tree and leaves every row standing as it was. The
panel reads the pair through `TreeLogicProtocol`, once per resolution, and a change of preference asks
each reconstruction browser for a redraw.

**A row the favorites mode holds back holds nothing it would show.** A row it shows either stands on
the way to a starred row or sits beneath one, and each of those facts holds for every row above it — so
declining a row declines its subtree, and one decision covers it while the traversal walks on.

**The shape the reader built is theirs to keep.** A browser holding `_REMEMBERS_EXPANSION` records
the rows standing open, by the tag those rows are addressed under, and a later pass creates them open
again: the filter adds the way down to what it names, and everything else comes back as it was left.
A row is recorded as it is collected, so what the filter unfolded is part of that shape too; a click
is read a frame later, once the row has answered it, and the expansion items record what they set. The
memory is held to the rows the model states, read afresh on every pass, so a row a moved
reconstructions directory left behind leaves the memory with it.

The shape outlives the run as well. A browser is handed the rows it stands open as it is built
(`initial_expanded_rows`), and `_persist_application_state` asks each tab for its shape and writes it to
`ApplicationState.expanded_rows` under the panel's tag. Reading it the once at exit keeps the session
free of a write per row per pass, a pass running on the tree worker.

**The Main tab's explorer remembers folders, not rows.** Its rows are the folders on disk, read a level
at a time as the reader opens one, so `ExplorerManager` holds two facts about a folder: whether its
children have been read, and whether its row stands open. They part company — a folder read and then
folded away is loaded and closed — and the open one is the shape a session writes to
`ApplicationState.expanded_directories`. A refresh reads down to each remembered folder through
`_expand_path_to`, reading every folder it needs once, and the folders that are no longer directories
are dropped as the manager is built.

**What the mode costs.** Resolving it walks the model once per rebuild, on the tree worker, testing
each row with `is_node_favorite` and `has_favorite_ancestor` — set lookups over `filepath.parents` —
and the anchors the preference follows are read out of that one answer. What it materialises is the starred rows and the rows
above them, and what reaches DearPyGui is the drawn rows alone: on a directory holding hundreds of
thousands of reconstructions, a favorites-only browser creates widgets for the starred ones and their
headings. A keystroke resolves the query alone, the drawn rows being the mode's to state. A favorite
toggled while the mode is on redraws the browser, so starring a row brings it in and unstarring one
takes it out along with what it held.

A rebuild that drew no row fills the cleared tree with the message naming the criterion that came back
empty (`global.dialog.message.tree_no_favorites`, `global.dialog.message.tree_no_results`), so the
filter's answer reads where the rows would be.

**The control** is a checkbox under the search box carrying the favorite glyph, which reads in the
favorite colour while the mode is on and muted while it is off. `_OFFERS_FAVORITES_FILTER` states
which cards hold it: the reconstruction browsers, whose rows stand for the paths a session stars. It
follows the tree's lock, a rebuild being what it asks for, and its label reads in the pair every
checkbox reads — the text colour while it can be clicked, the muted one while a rebuild holds it — so
the shade states whether the control is live.

Each browser opens in the mode it was left in. The panel raises `on_favorites_filter_changed` with its
own tag, and the tab coordinator writes it to `ApplicationState.favorites_filters` under that tag,
which is how a collapsed card is remembered too.

**Folding the whole tree away** is the other control every card carries. It reaches the rows through the
model rather than the widget tree, so one pass covers a branch however deep it runs, and it records what
it set — leaving the memory empty, which is the shape a later pass then draws. The explorer folds first
and drops the folders it had read afterwards, so opening one lists it as it stands on disk.
