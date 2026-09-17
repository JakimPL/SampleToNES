# Data Compatibility

This document governs the version upgrades applied to the stored data formats of
_SampleToNES_: reconstruction files (`.stn`), instruction libraries (`.ins`), and
project documents (`project.json`). Consult it when changing a serialized shape,
adding a format version, or diagnosing a file that loads as incompatible.

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

That step shows the shape a whole step takes, and it is four operations wide. It
lets the stored audio go, since a 2.2 reconstruction renders its channels from
the instructions it keeps; it names each stored stream by the channel that plays
it, where 2.1 named it by its generator; it stamps the configuration the file
carries with the version its shape now matches, which the load contract reads
alongside the outer metadata; and it states the record of the one recording the
file answered to — the channels the run handed out and the level it drove them
at, the file it was read from, and the frame-by-frame account of what it holds,
where a frame that sounds answers to the recording and a silent one answers to
rest.

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
mapping for `.stn` and `.ins`, the JSON document for `project.json`. The
transform steps reshape that payload — renaming the fields whose names changed
between versions, and adjusting the values they hold where the shape demands it.

A step also restates a value an older version computed, wherever the stored value
determines the current one in closed form: `compatibility/library/v2_1.py` recovers
each windowed candidate's mean spectrum from the `f(ΣS) / f(N)` data version 2.0
stored for its phase spectra `S`. Such a step holds its own copies of the computation
and the constants it used, so it reads the files of its version the same whatever
later builds make of them.

### A completed upgrade stamps the version it reached

A payload whose chain ran carries the new version in the same field it declares
it with, so the file states the version its shape now matches and a later save
writes that version. The load path leaves the bytes of every other payload
untouched.

## Mechanics

### Package layout

- `compatibility/kind.py` — `ObjectKind`, the format an upgrade belongs to
  (`LIBRARY`, `RECONSTRUCTION`, `PROJECT`).
- `compatibility/update.py` — `VersionUpdate`, one named version step.
- `compatibility/upgrade.py` — the engine: `upgrade`, `upgrade_binary`,
  `upgrade_json`, and the per-format registries `CURRENT_VERSIONS` and `UPDATES`.
- `compatibility/<format>/__init__.py` — that format's `UPDATES` tuple. The
  reconstruction chain currently holds the 2.1→2.2 step
  (`compatibility/reconstruction/v2_2.py`), the project chain the 1.0→1.1 step
  (`compatibility/project/v1_1.py`), and the library chain the 2.0→2.1 step
  (`compatibility/library/v2_1.py`).

### Version fields

- `.stn` — `metadata.reconstruction_data_version`
- `.ins` — `metadata.library_data_version`
- `project.json` — `format_version` at the document root

### Load boundaries

`Reconstruction.deserialize_data` and `InstructionLibraryData.load` pass their
payload through `upgrade_binary`; `ProjectContainer.load` passes the document
through `upgrade_json`. Each wrapper parses the payload, reads the format's
version field, runs the chain, and re-encodes the upgraded payload. A payload
that stays as it is — no chain applies, no version field, or a payload that does
not parse to a mapping — returns as the same bytes, so the load path behaves for
it exactly as it did before the upgrades existed. A file whose version no chain reaches arrives at the format's load contract
unchanged, which refuses it with the format's `Incompatible*VersionError`, as it
always did.

### Adding an upgrade

Read the format's version constant against the one the last release shipped, and
take whichever route that comparison names.

**The constant stands where the release left it.** The change opens a new step:

1. Bump the format's version constant in `sampletones_shared/application.py`.
2. Add the step module named after the new version — e.g.
   `compatibility/reconstruction/v2_2.py` — with a transform that takes the
   payload at the previous version and returns it at the new one.
3. Append the step to the format's `UPDATES` tuple.
4. Cover the step with unit tests under
   `tests/unit/sampletones_core/compatibility/`, and hold it to the archived file
   its base version names (see [The corpus](#the-corpus)).

**The constant already stands ahead of the release.** The pending step is the
one to widen: fold the new transform into the module named after that version,
state the whole step from the shipped version in its docstring, and extend its
tests to cover what was added. The version constant stays where it is.

The engine stamps the new version once the chain runs, so a step module declares
only its own transform.

## The corpus

A step tested against a payload the test builds itself is held only to the fields
whoever wrote the test thought to name. `tests/data/compatibility` keeps one
stored document per format per shipped data version, written by the build that
shipped it, and `tests/integration/compatibility` opens each one through that
format's own load entry point and holds the loaded model to the current shape.
The corpus states its own rules in `tests/data/compatibility/README.md`.

Two of those tests hold the corpus itself together: a file states the version its
name says, and every registered step reads a version the corpus keeps. The second
is what makes opening a step and archiving the file it reads one act rather than
two.

### Archiving a release

From a checkout of the release, once the version constants have moved:

```
uv run sampletones compatibility
```

A version already archived stands as it was written, since replacing a file would
restate history under a name that already means something.

### Backfilling a release that predates the command

Run the writer inside a worktree at that tag, keeping the port beside the files it
wrote:

```
git worktree add <scratch>/<tag> <tag>
cd <scratch>/<tag> && uv sync --frozen
cp <checkout>/tests/data/compatibility/generators/<tag>.py .
uv run python <tag>.py --output <checkout>/tests/data/compatibility
cd <checkout> && git worktree remove --force <scratch>/<tag>
```

The sync runs in the worktree rather than against the current environment because
a stored document names the release that wrote it, which the package's own
installed metadata answers for.

## Verification

- `uv run pytest tests/unit/sampletones_core/compatibility` covers the engine and
  every registered step against payloads built for it.
- `uv run pytest tests/integration/compatibility` opens the archived documents and
  holds them to the shape this build reads.
