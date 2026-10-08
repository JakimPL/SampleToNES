# Assets

This document governs `assets/`, the checkout unit that makes the repository's own content: the icon suite
the application ships, the demo tree, and the pictures of the application the guide and the README show.
Consult it before adding something the repository keeps that a person would
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
`build/` and is run by hand. A maker whose output may differ by a pixel between machines, as a software
renderer's does, is run by hand too, and the pull request shows what changed.

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

### Pictures

`assets/pictures/` draws the pictures the guide and the README show: the application running on the demo
tree, put into a state and read off the screen. A picture is a *scene*, written the way a screen scenario
is ([screens](application/screens.md)): a method under `assets/pictures/scenes/` takes the screen and the
`pictures` writer, drives the application through the automation unit's views and steps, and writes one
picture, cropped to the card, dialog or popup the page names, with a margin around it. The README's picture
is the whole window at twice the width the README shows it at; the guide's pictures come from a window at
the application's own minimum size, so a crop stays compact. Every picture is lossless, so what the page
shows is what the screen drew.

`make pictures` runs the scenes. The runner makes the demo tree under `build/demo` where it is missing,
starts the scenes under pytest on a few virtual displays of their own, with the scene naming in place of
the test naming, a screen large enough for the README's window, the records of each scene under
`build/pictures/`, and the scenario homes there too when the checkout's path holds no hidden folder, so a
path a picture shows reads as one under `/home`. The frame-rate reading is off in every scene, since it
would change the picture on every run. A scene's own window size and world come from
`assets/pictures/worlds.py`.

A picture is regenerated on purpose, by running the maker again after a change to the interface, and the
pull request shows the pictures that changed. A software renderer lands an anti-aliased edge a fraction of
a pixel differently from one process to the next, which flips a scatter of single pixels along text and
plot edges on every run, and a lossless file would carry every flip as new bytes. The writer therefore
keeps the picture that stands when a new drawing differs from it by that scatter alone, and rewrites it
when any small block of the frame changed as a whole, which is what a changed glyph, a moved control or a
redrawn line does. A run after no change to the interface leaves the repository as it was.
