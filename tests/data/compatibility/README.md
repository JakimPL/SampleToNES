# The compatibility corpus

One stored document per format per shipped data version, written by the build that shipped it.

The upgrade steps in `sampletones_core/compatibility` carry a stored file from the version a
release wrote to the version this build reads. These files are what that claim is held to: a step
tested only against payloads a test builds itself is held only to the fields whoever wrote the test
thought to name, and a field that changed shape while no step named it passes unnoticed.

A library another version wrote is rebuilt, and it is archived all the same: a library a release
wrote is held to reading as out of date, and a library archived at the version this build writes
is held to what this build generates for the same tones.

## Layout

A file is named after the **data version it was written at**, in the spelling the step modules use,
so a step and the file it reads are named alike — `compatibility/reconstruction/v2_2.py` carries
`reconstruction/v2_1.stn` forward.

```
reconstruction/v2_1.stn     written by 0.3.1
library/v2_0.ins            written by 0.3.1
project/v1_0.stp            written by 0.3.1
generators/                 the code each set was produced with
```

The release that wrote a file is inside it, as `metadata.version`.

## What a document holds

Small, and complete in shape: every field the format can store, with as little data in each as
states it. The reconstruction sounds all four channels, three frames each — one sounding, one
silent, one sounding — because rest and silence naming the same frames is a rule a stored record
is held to. Its recording is named by a relative path, so the file reads the same on every machine.
The project arranges one reconstruction under two voices, which is what holds a stored project to
keeping a single copy of it, and its embedded reconstruction names no file, the way a project
detaches a recording before storing it.

The library holds two measured tones at a low sample rate, which keeps the file small.

## Adding a version

At each release, from a checkout of that release:

```
uv run sampletones compatibility
```

It writes one document per format at the versions that build states, and leaves alone any version
already archived — replacing a file would restate history under a name that already means
something. The corpus grows by one file per format per version, and never changes underneath.

A version that shipped before the command existed is backfilled once, from a worktree at its tag,
with the generator kept under `generators/`. The recipe is in
[Data compatibility](../../../docs/development/release/compatibility.md).
