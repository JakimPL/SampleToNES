# Colors and Palettes

This document describes how a color is written, composed, and handed to DearPyGui, and what a
palette change costs. It governs `utils/palette/` and `utils/gui/palette/`. Consult it when adding a
color the interface draws with, or a shade the interface derives from one.

The design truth it realizes is principle 13 of [`architecture.md`](../architecture.md): a color is a
token, resolved where it is drawn. This document holds the mechanism.

---

## A color is a token

Every annotation names `BaseColor` (`utils/palette/colors/`): a dataclass field, a signature, a dictionary
key. `WrittenColor` appears only on the Pydantic field that validates a YAML entry, the one place a written
token is read out of the configuration. The `rgba` read happens where the value is handed to a widget, and
a consumer keeps the token, so whoever holds a color follows a palette swap.

## A shade is composed by naming its form

`utils/palette/colors/` has one module per form. `base.py` declares the abstract `rgba`, and each form is a
peer module beside it (`literal`, `named`, `faded`, `grayscale`, `blended`, `layered`) that answers with a
`BaseColor` of its own, for example `FadedColor(color=GrayscaleColor(color=token), fraction=0.3)`. Every
form is a module-level frozen dataclass, so two identical compositions are one value and a theme cache
keyed on a shade hits.

## A palette change is one switch

DearPyGui copies a color when it receives it. `PaletteBindings` (`utils/gui/palette/`) therefore records
each `(item, argument)` a palette color reached, and `dpg_set_palette_color` and
`dpg_add_palette_theme_color` are how a color gets there.

`PaletteSource.activate` then fires the composition root's listener. The listener re-applies the bindings,
refreshes the viewport clear color, and repaints the sequencer for the row and cell highlights DearPyGui
keeps as table state.

The `palette-colors` hook reports each of these: an attribute assigned a resolved `rgba`, a theme color
filled outside the palette bindings, and a hex literal in the shipped configuration outside `palettes/`
(see [`architecture.md`](../architecture.md#enforcement)).
