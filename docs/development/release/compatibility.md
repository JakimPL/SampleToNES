# Data Compatibility

This document governs the data versions of the stored formats of _SampleToNES_:
reconstruction files (`.stn`), instruction libraries (`.ins`), and project
documents (`project.json`). Reconstructions and projects are upgraded; libraries
are rebuilt. Consult it when changing a serialized shape, adding a format
version, or diagnosing a file that loads as incompatible.

The upgrades live in `sampletones_core/compatibility` and run at the load
boundary of each format, before deserialization. The formats' own documents
describe their stored shape and versioning:

- [`formats/reconstructions.md`](../../formats/reconstructions.md)
- [`formats/instruction-libraries.md`](../../formats/instruction-libraries.md)
- [`formats/projects.md`](../../formats/projects.md)

## Principles

### A format reads and writes one data version

Each format states the single data version this build produces, held in
`SAMPLETONES_LIBRARY_DATA_VERSION`, `SAMPLETONES_RECONSTRUCTION_DATA_VERSION`,
and `SAMPLETONES_PROJECT_DATA_VERSION` (`sampletones_shared/application.py`).
The version travels inside every stored file, and the format's load contract
holds each file to it: `MetadataContract` for the binary formats, the
`format_version` check for projects.

### An upgrade is one version step

A stored shape changes in small, named steps. Each step is a `VersionUpdate`:
the version the payload reads at, the version it writes after the transform, and
the transform itself. The steps of one format form a chain, registered in
`compatibility/<format>/__init__.py`, and each step lives in a module named
after the version it writes — `compatibility/reconstruction/v2_2.py` carries
the step that writes reconstruction data version 2.2.

**A step owes only what a release wrote.** The shape a payload reaches is what
the model reads, and a model reads the fields it declares: a key the current
shape has no field for is never looked at, so a step that renames or removes one
is doing nothing. The 2.1 step therefore leaves the retired configuration
settings where they stand and spends its effort on the sections the document is
read from.

### A version belongs to a release

The version a format writes moves once per release. Between releases that
version is still being written: every file carrying it was written by a working
tree, so a further change to the stored shape extends the step already pending
rather than adding a second one, and that step widens to carry the whole
distance from the version the last release shipped. What a user's files travel
is therefore one step per release, and `git show <tag>:src/sampletones_shared/application.py`
names the version their files stand at.

### A chain applies whole or not at all

An upgrade runs only when the registered steps form a complete path from the
file's version to the version this build writes. A file whose version no chain
reaches comes back unchanged, and the format's load contract refuses it, exactly
as it refuses any version this build does not support. A partial path leaves a
file entirely untouched.

### Upgrades run on the raw payload

Upgrades apply to the serialized payload before any model sees it: the msgpack
mapping for `.stn`, the JSON document for `project.json`. The
transform steps reshape that payload — renaming the fields whose names changed
between versions, and adjusting the values they hold where the shape demands it.

### A library is rebuilt from its settings

A library is derived data: its `InstructionsLibraryConfig` and the generators
determine it wholly, and generating one costs about what measuring its entries
costs. A library written at another version is therefore rebuilt:
`LibraryState` reads the version from the metadata that leads the file, and a
file the load contract would refuse reads as out of date. A conversion — in the
application, headless, or in calibration — rebuilds the library it needs
unprompted, and opening one from the _Instructions_ tab asks first.
Reconstructions and projects carry their own configuration, so what a user made
stands apart from the libraries it was converted with.

The library version names what generation produces, so any change to the
generators or to feature extraction bumps it, and the bump alone carries the
change to every stored library. The corpus keeps libraries all the same: a
library a release wrote is held to reading as out of date, and a library
archived at the version this build writes is held to what this build generates
for the same tones.

### A completed upgrade stamps the version it reached

A payload whose chain ran carries the new version in the same field it declares
it with, so the file states the version its shape now matches and a later save
writes that version. The load path leaves the bytes of every other payload
untouched.

## Adding an upgrade

Read the format's version constant against the one the last release shipped, and
take whichever route that comparison names.

**The constant stands where the release left it.** The change opens a new step:
bump the constant, add the step module named after the new version with a
transform from the previous version to it, append the step to that format's
chain, and cover it both with unit tests and against the archived file its base
version names. A library change takes the version bump alone, since a library is
rebuilt rather than upgraded.

**The constant already stands ahead of the release.** The pending step is the one
to widen: fold the new transform into the module named after that version, state
the whole step from the shipped version in its docstring, and extend its tests to
cover what was added. The version constant stays where it is.

The engine stamps the new version once the chain runs, so a step module declares
only its own transform.

## The corpus

A step tested against a payload the test builds itself is held only to the fields
whoever wrote the test thought to name. `tests/data/compatibility` keeps one
stored document per format per shipped data version, written by the build that
shipped it, and `tests/integration/compatibility` opens each one through that
format's own load entry point and holds the loaded model to the current shape.

Two of those tests hold the corpus itself together: a file states the version its
name says, and every registered step reads a version the corpus keeps. The second
is what makes opening a step and archiving the file it reads one act rather than
two.

The corpus states its own rules, and how a version is written into it, in
`tests/data/compatibility/README.md`.
