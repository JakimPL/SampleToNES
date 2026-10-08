# Assets

This document governs `assets/`, the checkout unit that makes the repository's own content: the icon suite
the application ships, and the demo tree the guide's pictures are drawn from. Consult it before adding something the repository keeps that a person would
otherwise draw, record or arrange by hand, and before changing how one of these is made. What a checkout
unit is, and what it may import, is in [tooling](tooling.md).

---

## Principles

**1. The repository's content is made from a specification, never by hand.** A thing the repository keeps
and shows, such as an icon, comes from a declaration of what it should be and a maker that renders it. A
change to the thing is a change to its specification, after which the maker runs again. The committed
files are the maker's output and nothing else, so a reader who wants to know why a thing looks as it does
reads the specification.

**2. One package per thing made.** Each package of the unit makes one kind of thing, says what it makes
and from what, and writes it where the thing is kept. It runs as `python -m assets.<package>`, with a parser
and help of its own, and the Makefile names it. `--output` (`-o`) sends the output elsewhere, which is how a
test or a trial run keeps away from the committed files.

**3. A maker whose output is the same on every machine holds the committed files.** The icons rasterize
the same on every machine, so the `icons` pre-push hook runs their maker for a push that touches the mark
or the icons, and a committed file that differs from what the mark describes fails the push. CI runs the
same hook. A maker whose output depends on the machine's arithmetic, such as a conversion, writes under
`build/` and is run by hand.

## The makers

### Icons

`assets/icons/` writes the icon suite from the mark declared in `assets/icons/mark/config`. `mark.yaml` has
the geometry, colors and rasterization settings, validated as a `Mark`, and `template.svg` is the vector the
rendered geometry fills. The suite is the vector `sampletones.svg` and the rasters the application ships,
`sampletones.png` and the multi-resolution `sampletones.ico`, written into the directory the icons ship
from, `src/sampletones_assets/icons/`. `make icons` writes them, and `python -m assets.icons -o DIR` writes
them elsewhere. The whole suite is committed, so every wheel, bundle and test run finds the icons where
they lie. Pillow rasterizes the suite; it is a development dependency, so the maker runs in a checkout alone.

### Demo tree

`assets/demo/` writes a documents folder a person can run the application from, with recordings beside
it, so the application has something to show without anyone's own files. Four specifications under
`assets/demo/config` say what it holds: `voices.yaml` declares synthesizer voices in the corpus's own
shape, `recordings.yaml` places them into hits struck once and a short piece of stems written as notes in
beats, `conversion.yaml` gives each hit its channels and the stems their levels, and `project.yaml` arranges
the hits and two instruments into a song. The maker renders the recordings, writes a configuration whose
library and reconstructions folders lie in the tree, builds that library, converts each hit alone and the
stems together, and saves the project. Each reconstruction names its recordings relative to the tree, so
the tree reads the same wherever it is put, and the application reaches them when it runs from inside it:
`cd DIR && sampletones -c config.json`.

`make demo` writes the tree under `build/demo`, and `python -m assets.demo -o DIR` writes it elsewhere;
the folder must be empty, which keeps a stale tree from mixing with a fresh one. The library takes the
longest part of a run, and the conversions run on whatever the machine offers, so two machines may convert
the same recordings into slightly different documents.
