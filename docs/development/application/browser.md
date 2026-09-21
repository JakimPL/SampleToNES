# The Reconstruction Browser

This document governs the tree of reconstructions the **Reconstruction** and **Sequencer** tabs share: how a reconstructions directory becomes rows, what a row stands for, and what it answers. Consult it when changing what the browser lists, how a row reads, or what a click on one does. It complements [`architecture.md`](../architecture.md) (layering and ownership) and [`guidelines.md`](../guidelines.md) (coding rules).

Four terms recur. A **row** is one line of the tree. A **heading** is a row the browser writes itself, such as a frequency pair or a source folder, as opposed to a row for a path on the disk. A **branch** is one of the two top-level views of the same reconstructions: the configuration branch lists them as the disk holds them, and the sample branch groups them by the audio they were made from. A **mode** is a state a browser can be in, such as showing favorites only.

---

## Principles

1. **One reading of the disk feeds every view.** A refresh walks the reconstructions directory once into a `ReconstructionScan`, and every branch is built from that record. The views therefore agree about what exists by construction, and a folder name is parsed into its configuration fields once per refresh.
2. **The model carries the shape, and the panel carries the widgets.** Which rows exist, what they are called, which of them fold together and in what order they sit are decided on the tree. Both tabs render one model, so they show one shape, and each rule can be exercised without a window.
3. **A row's identity is its path, and its name is a label.** Favorites, the context menus, copy-path, playback and opening a reconstruction all key on `filepath`. That frees a name to be rewritten: a configuration directory renamed to its channel abbreviation, a chain of headings joined into one row, a colliding label marked with its configuration hash.
4. **The browser writes the headings the disk implies.** A frequency pair, a transformation, a source folder and one source audio each become a row that has no path of its own. What such a row offers follows from the subtree beneath it.
5. **One thing may stand in several places.** A reconstruction is listed by the configuration that produced it and again by the audio it was made from. An action on the thing, and not on the row, asks for every row standing for it (`Tree.find_nodes`, `BrowserManager.nodes_at`) and hands them to both tabs.
6. **Per-row work happens off the main thread.** A rebuild resolves each row into a `NodeSpec` on the background worker (tag, label, font, theme, handler, open state), and the main thread creates the widgets from those specs, spread across frames.
7. **What a browser narrows to is its own.** Both tabs render one model, so the panel showing a browser decides which rows it shows. A search typed in one tab leaves the other reading as it was, and each browser opens in the mode a session left it in.
8. **The reader's shape is theirs to keep.** Which rows stand open is what the reader made of the tree, so a browser records it and brings it back. A refresh, a change of filter and a repaint leave the tree standing as it was, and so does the next run of the application. What a filter unfolds on top of that shape is remembered as the filter's own. It is held for as long as the filter is and handed back when the filter goes. The one exception is a row the reader's own opening has come to stand on, which stays open so the view they built stays on the screen.

---

## The two branches

A refresh walks the directory once, and both branches are built from that one scan. The configuration branch lays the scanned folders out as they sit, giving each configuration directory a friendly name. The sample branch regroups every top-level configuration directory's reconstructions by the audio they mirror, and gathers each audio's variants under one sample row, each labeled by its configuration. A heading is extended and not repeated: one of that name is looked up among the siblings of its own kind and class, so a folder and an audio sharing a name stay two rows.

The two branches share a policy. A configuration directory at the top level of the reconstructions directory is the one lifted under groups and transposed into the sample view. A configuration directory nested inside a plain folder keeps its friendly name where it sits. A reconstruction outside every configuration directory appears in the configuration branch, since that branch follows the disk.

Which row carries the configuration follows the branch. In the configuration branch it is the directory that names it. In the sample branch it is the variant leaf, since there the configuration is what distinguishes one row from the next.

## The shaping rules

* **Prune.** A heading the browser wrote that gathers nothing leaves, deepest first, so a whole chain of them goes at once and a reconstructions directory with nothing to show stays silent. A folder the disk holds stays, since the configuration branch mirrors the disk.
* **Collapse.** A heading above a single row folds into that row, which takes the joined name and rises into its place. The surviving row keeps its node type, path, configuration and children, so its click behavior, theme, context menu and favorite star carry over. A fold that would repeat a name already beside it stays open, and the branch roots stay in place. With a single configuration present, the configuration branch reads as one row per reconstruction, and it grows back into groups as soon as a second configuration arrives.
* **Order.** Containers come ahead of leaves, then rows follow a natural sort over the label, so a row sits where its displayed name puts it and `8 kHz` precedes `44.1 kHz`. The pass runs once every label is final. The branches directly under the container root keep the order the builder gives them.
* **Unique sibling labels.** Where siblings would read alike, every member of that label takes its short configuration hash. One rule serves the channel directories under a transformation group, the nested configuration directories, and the variants under a sample.

## Rebuilds and rows

**One rebuild is in flight at a time.** A browser is asked to rebuild from either tab and from several places in the application. A rebuild starts on the tree worker, which takes the tree lock, brings the model up to date, collects the rows into specs and hands them to the emitter. The emitter clears the old rows and stages the new ones in budget-sized batches, so interactive callbacks run between slices. A whole-tree rebuild asked for while the lock is held, by another rebuild, a library load or a library generation, is kept for the release. The release asks for it again once the tree stands free, and the latest request is the one kept.

**A row's tag is composed and not stored.** The tag joins the names above the row, which reads the row back to whoever inspects the widget tree, and it appends a digest over the exact path of `(node_type, name)` pairs. Rows the names alone spell alike, such as a folder and the audio beside it or two labels that differ only in spacing or case, therefore keep tags of their own. Since a tag is composed, any holder of a node can address its row. That is how expanding a subtree, repainting a star and applying a filter reach the widgets.

**What a row answers follows its kind.** A reconstruction plays on a click, opens on a double click, and offers its path items, the tab's own actions and the favorite mark. A directory offers its path items and the favorite mark. A group or a sample stands for no path, so its menu reads the subtree: how many reconstructions it gathers, expanding and collapsing everything below it, the label the tree shows it by, and, on a sample, the audio its reconstructions were made from, answered through any one of them.

**Favorites are paths.** A row is a favorite when its path is in the session's set, and it reads as part of a favorite folder when any of its parents is. A reconstruction therefore reads as part of a favorite folder wherever a view puts it, including the sample branch, whose headings carry no path. One path reaches the panel as several rows, so `application.py` resolves the toggled path into every row standing for it and hands them to both tabs. Each row repaints with the ancestry its own path carries.

## Filtering

`TreeFilter` holds what a browser is currently asked to show, and the panel showing it owns the filter. It is given whole and replaced whole (`with_query`, `with_favorites_only`), so one place resolves what the browser shows. `NO_FILTER` is the filter a browser showing its whole tree holds.

The two criteria answer different questions, so each lands in a different place:

| Criterion | What it decides | Where it lands | What a change costs |
|---|---|---|---|
| `favorites_only` | which rows the browser **draws** | the rows the mode shows are the rows collected into specs, so `TreeEmitter` creates widgets for those alone | a redraw: the rows are collected again from the model in hand, on the tree worker |
| `query` | which of the drawn rows are **shown** | `show` is flipped over the rows already on screen, once the typing settles | a resolution of the query, debounced |

One rule serves both. `TreeVisibility` takes the rows a criterion named and answers which rows stay: a named row, a row leading down to one, and a row one holds. It keeps the named rows and the rows above them, so what a pass holds in memory follows the size of what was found, and a row beneath a match is answered from its own path upward.

**What a criterion names and what it keeps are two sets.** A criterion points the reader at some rows and brings others along with them, and only the first kind is worth unfolding to. The rows a criterion names are its **anchors**. For a search, the anchors are the rows whose label matched. For the favorites mode, an anchor is a row a star sits on, or, where no row stands for the starred path, the shallowest rows that path reaches. In the sample branch the headings carry no path, so the variants are the rows a starred folder arrives at.

**A criterion is read the way that criterion means.** A search shows what a matching row gathers, so a match opens along with the rows above it. The favorites mode points the reader at a star, so what opens is the rows above it, while the star's own row stands where the reader left it. A starred folder is therefore revealed. A starred reconstruction inside a starred folder anchors on its own, which is what opens the folder above it.

**Which stars are followed is the reader's.** The mode decides what is drawn. Whether it also unfolds is a preference given per kind of favorite, held in the application's browser configuration. A starred reconstruction reads the preference for reconstructions. A starred folder, and everything it brings in where no row stands for it, reads the preference for directories. By default both are off, so turning the mode on narrows the tree and leaves every row standing as it was. The panel reads the pair through `TreeLogicProtocol`, once per resolution.

**An opening belongs to the pass that asked for it.** Switching the mode on is the reader asking to be shown their favorites, so the pass that switch starts is the one that follows a star, and the rows it opens are noted in the mode's own memory. Later passes read that memory. A refresh, a query or a star gained meanwhile therefore leaves the reader looking at their favorites, while the stars followed stay the ones the switch asked about. The pass that reads the mode off lets the memory go, and those rows fold back. A change of preference asks for nothing. It is answered the next time the reader asks for the mode, which keeps a menu click from moving the tree the reader is working in.

**A row the favorites mode holds back has nothing it would show.** A row the mode shows either stands on the way to a starred row or sits beneath one, and each of those facts holds for every row above it. Declining a row therefore declines its subtree, and one decision covers it while the traversal walks on.

**Two memories, each holding what one hand opened.** `RowExpansionMemory` (`ui/elements/tree/expansion.py`) owns both and the rules that join them. It holds each row by the tag it is addressed under, so a later pass creates the row open again.

- The reader's rows hold what the reader did: a click, the expansion items, the collapse control. A session writes them down.
- The mode's rows hold the way down it opened, and they go when the mode does. A narrowed browser therefore hands the tree back the way the reader had it.

Where the reader's own rows have come to stand on a row of the mode's, the memory takes that way down over as the reader's, so the view they built stays on the screen (principle 8). Folding a row is the reader's word on it whichever hand opened it, so the row stays folded. A pass writes from the tree worker while a click writes from the main thread, so one lock covers every answer the memory gives. Both sets are held to the rows the model states, read afresh on every pass, so a row a moved reconstructions directory left behind leaves them with it. Each browser is configured to record a shape or not, and a browser that records none leaves the memory empty.

A search unfolds by the same rule from the other end: its matches and the rows above them open for as long as the query stands, resolved afresh on each pass, and clearing the query folds them back.

**The shape outlives the run.** A browser is handed the mode and the rows it opens with as it is built, reports a change of mode where it happens, and is asked for its shape once, at exit. Each tab's rows go to `ApplicationState.expanded_rows` under the panel's tag, and its mode to `ApplicationState.favorites_filters` under the same tag. A browser therefore opens in the mode it was left in, with the rows it was left with, and a collapsed card is remembered the same way.

**The Main tab's explorer remembers folders.** Its rows are the folders on disk, read a level at a time as the reader opens one. `ExplorerManager` therefore holds two facts about a folder: whether its children have been read, and whether its row stands open. They part company, since a folder read and then folded away is loaded and closed. The open one is the shape a session writes to `ApplicationState.expanded_directories`. A refresh reads down to each remembered folder, reading every folder it needs once. A remembered folder the disk no longer holds is read down to as far as it still stands and stays remembered, so a drive unplugged for one run opens where it was left once it is back.

**What the mode costs.** Resolving the mode walks the model once per rebuild, on the tree worker, testing each row's path and its parents against the session's set. The anchors the preference follows are read out of that one answer. The resolution materializes the starred rows and the rows above them, and what reaches DearPyGui is the drawn rows alone. A favorites-only browser therefore creates widgets for the starred reconstructions and their headings and not for the whole tree, even over a very large directory. A keystroke resolves only the query, because the mode decides the drawn rows. A favorite toggled while the mode is on redraws the browser, so starring a row brings it in and unstarring one takes it out along with what it held.

A rebuild that drew no row fills the cleared tree with the message naming the criterion that came back empty, so the filter's answer reads where the rows would be.

**The controls each card carries.** A checkbox under the search box switches the favorites mode. Only the reconstruction browsers hold it, because their rows stand for the paths a session stars, and it follows the tree's lock, since a rebuild is what it asks for. Folding the whole tree away is the other control. It reaches the rows through the model and not the widget tree, so one pass covers a branch however deep it runs, and it records what it set, which leaves the memory empty. The explorer folds first and drops the folders it had read afterward, so opening one lists it as it stands on disk.
