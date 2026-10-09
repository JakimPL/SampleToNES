# Progress

This document governs how a long operation says how far it has come, and how that account reaches
the reader watching it. Consult it when adding an operation that takes long enough to be watched,
when changing what one reports, or when the report has to cross a process boundary.

The subsystem spans several packages. The operations that report live in `sampletones_core` and
`sampletones_player`. The line a report crosses between processes is
`sampletones_core/parallelization/channel/`. The layer that draws it is `sampletones_application/services/`
and `logic/`. [`packages.md`](packages.md) describes the layering between those packages, and
[`architecture.md`](architecture.md) describes the application's own layers.

---

## Principles

### 1. A run reports where it stands and hears whether it is still wanted

Every long operation reports through one shape: a callable taking what the run has reached and
answering whether the run goes on.

```python
ExportReporter = Callable[[ExportProgress], bool]
```

Each domain names its own progress type (`ExportProgress`, `WalkProgress`, `CodecProgress`,
`ReconstructionProgress`) and its own `announce`. `announce` builds that type, offers it, and raises
`OperationCanceled` where the answer is no. One reporter therefore carries both directions: an operation is
watched and withdrawn over the same line. A caller that wants neither passes `silent_reporter`
(`sampletones_shared/utils/progress.py`) and hears the run through to its end.

### 2. A stage names the unit its counts are in

A run passes through stages counting in units of their own: a song's ticks, a dictionary's bytes, a
recording's frames, a batch's files. A report therefore names its stage, and the name says what the counts
mean. `ExportStage` and `ReconstructionStage` are the vocabularies.

Where the stages differ in what they cost, the enum says what each is worth against the others
(`STAGE_WEIGHTS`), so one reading spans a run that changes what it is counting several times over. The
weights are approximations measured over whole runs, and they are justified by what they achieve: a bar
that tracks the time a run actually takes. They are counts and not fractions. A reading divides them once
at the point of use, so a finished run arrives exactly at its end.

### 3. A report is filed as often as the run moves, and carried as often as it is worth reading

An operation announces every step it makes, every frame and every row, because that is what it knows.
Whoever carries the report decides how often that is worth passing on. `ReportRate`
(`sampletones_shared/utils/progress.py`) spaces reports over `PROGRESS_STEPS` whatever the stage counts in.
It always takes a stage's first reading and its last, and it treats a count that falls as a step, the same
as one that rises.

Both carriers use it: `StageProgress` in the application services, and `JobReporter` in the conversion.
`JobReporter` throttles on the worker side, so the line between processes carries only what a bar can be
redrawn at.

### 4. A run reports in items when it has many, and in the part done of one item when it has one

An operation counts the items it is measured in: files, samples, jobs. Where it is measured in many items,
that count is the reading. The items are what a reader recognizes, and a run with several under way at
once has no one item to follow. Where it is measured in one item, the count stands at nothing out of one
for the run's whole length. The reading is then the part of that one item done, which the item reports
itself.

Both layers carry the same pair, and each tells through `is_single` which of the two it is:

| Layer | Type | The counts | The work under way |
|-------|------|-----------|--------------------|
| Core | `TaskProgress` | `completed` / `total` | `steps`, one per running task |
| Application | `ServiceProgress` | `completed` / `total` | `partial`, in items |

Both derive `fraction` from them. The layer that turns a run's account into a result states the unit that
run reads in (`ConversionService` does it for a conversion). The count a status line prints, the stage it
names, the bar it draws and the estimate beside it therefore all answer in that one unit. The logic layer
reads them under `logic/main/converter/`, and `ETAEstimator` (`parallelization/progress.py`) makes the
estimate from what a run has covered.

### 5. A task reaching another process reports over a channel

Where an operation runs in a worker process, its reports reach the run over a `ProgressChannel`
(`sampletones_core/parallelization/channel/`). The channel carries both directions of principle 1 across
the boundary, and callers depend on the Protocol and not on any one way of crossing it.

`ProcessProgressChannel` is the implementation. A manager stands beside the pool and owns both ends: a
queue that reports travel up, and a flag that a withdrawal travels down. Both live under the same spawn
context the pool's workers run in. Each end reaches a task as an ordinary value it is built with, so a
worker started as a fresh interpreter reconnects on its own. That makes one channel serve every platform.

---

## Mechanics

**Reading the channel belongs to a thread of its own.** A run's monitor thread waits on the results the
pool hands back, so a separate thread (`ProgressPump`) reads the channel. It takes everything already
waiting in one turn and announces once. That holds the announcements to the rate it reads at, however many
steps the tasks file in between.

### A finished task stays finished

A task's reports travel a line the run reads at its own pace, so a report filed before a task's result
arrived may be read after it. The run records the tasks it has counted (`TaskSteps`) and lets their later
reports go. That keeps a task's own progress and the run's completed count from describing the same work
twice, and it keeps the reading inside the run it describes.

### The pool's and the channel's lifetime

The run's monitor thread (`TaskProcessor`) is the one owner of its pool. However the run ends, the monitor
ends the pool: a finished pool winds down, and a canceled or failed one is stopped. It then reaps the
workers, closes the channel, and only then announces the outcome.

`cancel()` withdraws the run and leaves the rest to the monitor. `shutdown()` cancels a run still going and
returns once the monitor has finished. The owner of a run (`InstructionsLibraryManager`,
`ConversionService`) lets it go only after `shutdown()` returns, so an operation reads as active until no
worker of it is left.

The channel is a process of its own. It opens on the first task that asks for a line and closes after the
pool, since the workers hold proxies to it. A run whose tasks report nothing never opens one.

---

## Testing

Progress is one path with two halves, and each is tested where it is cheap to test. A stage's share, the
spacing between reports and a late report are unit-tested beside the code that decides them. The pipeline
reporting its stages and the line carrying a report between processes are held by integration suites.

The two cross-process suites run real worker processes and put something cheap in place of the work:
counting in one, a walk through the stages in the other. They measure the wiring and not a reconstruction.
Both hold their worker at a chosen point until the test has taken the reading it asserts on
(`tests/suite/release.py`). An assertion about work under way is therefore made while that work is provably
under way, and does not rest on the scheduler.
