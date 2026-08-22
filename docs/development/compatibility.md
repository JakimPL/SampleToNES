# Data Compatibility

This document governs the version upgrades applied to the stored data formats of
_SampleToNES_: reconstruction files (`.stn`), instruction libraries (`.ins`), and
project documents (`project.json`). Consult it when changing a serialized shape,
adding a format version, or diagnosing a file that loads as incompatible.

The upgrades live in `sampletones_core/compatibility` and run at the load
boundary of each format, before deserialization. The formats' own documents
describe their stored shape and versioning:

- [`formats/reconstructions.md`](../formats/reconstructions.md)
- [`formats/instruction-libraries.md`](../formats/instruction-libraries.md)
- [`formats/projects.md`](../formats/projects.md)

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

That step shows the shape a whole step takes: it names each stored stream and
approximation by its channel, names the embedded config's channel selection the
same way and stamps that config with the target version, lists the source audio
as one path per stem, and synthesizes the stems record every 2.2 file carries —
one stem covering every enabled channel and holding every frame the file plays,
which is what the conversion that wrote the file did.

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
  (`compatibility/project/v1_1.py`), and the library chain is empty.

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

1. Bump the format's version constant in `sampletones_shared/application.py`.
2. Add the step module named after the new version — e.g.
   `compatibility/reconstruction/v2_2.py` — with a transform that takes the
   payload at the previous version and returns it at the new one.
3. Append the step to the format's `UPDATES` tuple.
4. Cover the step with unit tests under
   `tests/unit/sampletones_core/compatibility/`, and with a loader test that
   opens a payload written at the previous version.

The engine stamps the new version once the chain runs, so a step module declares
only its own transform.

## Verification

- `uv run pytest tests/unit/sampletones_core/compatibility` covers the engine and
  every registered step.
- The format load tests open payloads at previous versions and hold the loaded
  models against the current shape.
