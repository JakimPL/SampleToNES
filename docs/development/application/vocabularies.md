# Identifier Vocabularies

Two vocabularies name things across `sampletones_application`: the keys every user-visible string is
looked up by, and the identifiers DearPyGui knows a widget by. Both are spelled by a grammar. A pre-commit
check, called a hook here, holds each one to the source across the whole tree. Each keeps in one place a
fact that would otherwise be restated at every use. Consult this document when adding a string the reader
sees, or a widget another module reaches.

The design truths it realizes are principles 8 and 9 of [`architecture.md`](../architecture.md): all
display text comes from `LanguageManager`, and `tags/` holds only DPG identifiers. This document
holds the grammar behind both.

---

## Display text

### The grammar

Every user-visible string is looked up on `LanguageManager` by the key the language file spells:

```
page.panel.text_type.element
```

The first three segments name members of `Page`, `Panel` and `TextType` (`categories/hierarchy.py`). The
element segment names a member of an element enum, which is any enum deriving from `AbstractElement`. An
element enum is found by what it derives from. One naming a panel's own widgets lives with the other panel
vocabularies under `categories/elements/`. One naming a domain's gestures, such as `HistoryAction`, lives
beside that domain and serves as both the value the domain records and the element its label is looked up
by.

`en.yaml` is a flat map keyed exactly this way, so the dotted string is the lookup form,
`language_manager["global.dialog.label.ok"]`, and a reader holds a key against the language file by eye.
`categories/key/` owns the grammar. `validate_text_key` checks every key the file holds at load time, and a
lookup that misses raises `MissingTextError` naming the key and the file. Log messages are developer-facing
and exempt.

### Text resolves where it is displayed

A class that reads text holds the manager as `self._language_manager`, assigned in its own `__init__`, and
looks each string up at the point of use, so a language change takes effect on the next read. A class that
inherits the manager declares it in its body instead, `_language_manager: LanguageManager`, which states
the same thing to a reader and to the hook. Where the same text is read at more than one site in a class,
one named binding serves them all and the reads stay in step.

### The forms a lookup takes

A key assembled at runtime passes its four members instead, as in
`language_manager[Page.SEQUENCER, Panel.ORDER, TextType.LABEL, element]`. The variable part is annotated as
the concrete element enum it carries (`SequencerOrderElements`, `DialogElements`). That annotation keeps
the key checkable: the `language-keys` hook expands it to the enum's members and holds every key it reaches
against the language file.

A lookup therefore states its key in one of the forms the hook reads values from: literals, annotated
members, or a conditional between two literal keys.

```python
language_manager[
    "global.pitch.label.period_name" if is_period else "global.pitch.label.pitch_name"
]
```

---

## Widget tags

### `compose_tag` is the one composer

`tags/compose.py` owns `TAG_SEPARATOR` and the joiner, and every tag reaches its final spelling through it.
Each part is lowercased and its whitespace runs become single underscores, so a tag built from a runtime
name, such as a sample title or a layer label, reads the same however that name arrives cased or spaced. A
part that already holds a composed tag contributes its own segments, which is how a child tag extends its
parent. Fragments hold bare segments (`SUF_GRAPH_PLOT = "plot"`) and gain separators only from the joiner,
so a fragment reads as the segment it names and either end composes onto it.

### A runtime name carries its identity beside it

The composer reads two names that differ only in case or spacing as one segment. A tag built from a name a
user gave, such as a file path or a project title, therefore carries `identity_part(*parts)` beside the
name. The part is a short digest of the name exactly as it arrived, so `Kick.wav` and `kick.wav` name
widgets of their own. The readable name stays in the tag, so a DearPyGui error still says which row it is
about.

`tags/compose.py` states the rule once over `sampletones_shared.utils.hashing.identity_digest`, which joins
the parts on a separator no name carries. `ui/elements/stems/tags.py` and `ui/elements/tree/tag.py` both
read it. A widget keyed by anything a user names needs it: DearPyGui refuses a duplicate alias, so two names
arriving at one tag break the draw.

### A whole tag is a `TagName`

`TagName` is the `str` subclass in `categories/key/tag.py` that names a tag's four parts and
composes them:

```python
TAG_MAIN_EXPLORER_TREE = TagName(
    Page.MAIN, Panel.EXPLORER, Widget.TREE, "explorer"
)  # main.explorer.tree
```

The spelling is `page[.panel].widget[.element]`. `Panel.IMPLICIT` names a widget that belongs to no panel,
and an element that repeats its panel's name is carried by the panel segment alone. A constant's name is
its composed tag upper-cased, with each separator turned into an underscore, behind the `TAG_` prefix.
Reading either one therefore gives the other, and the `tag-names` hook holds the two together.
