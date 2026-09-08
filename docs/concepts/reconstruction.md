# Reconstruction algorithms

This document explains how _SampleToNES_ turns an arbitrary audio sample into a
*reconstruction* — a sequence of NES instructions that, when played back on the
console's sound hardware, approximates the original. It is written to be readable
without prior knowledge of the codebase, while pointing at the packages that
implement each part.

The tunable choices described here are set empirically; the experiment that
picks them is described in [Calibration](calibration.md).

## 1. The problem

The NES sound chip (Ricoh 2A03 APU) can only produce a few simple, fixed
waveforms across four usable channels:

- two **pulse** (square) channels — each with 4 duty cycles and 15 volume levels;
- one **triangle** channel — fixed shape and amplitude, pitch only;
- one **noise** channel — a pseudo-random LFSR generator with 16 periods, 15
  volume levels and a short/long mode.

A program steers these channels by issuing *instructions* a few dozen times per
second (for example, *pulse 1: note A-4, volume 12, 50 % duty*). Approximating an
arbitrary sound this way produces a **reconstruction**: one instruction stream per
channel whose mixed, rendered output resembles the input as closely as the
hardware permits. By default a reconstruction uses one pulse channel, the triangle
and the noise; the second pulse can be enabled in the configuration. The channel
models live in `sampletones_core.generators` and the instruction value types in
`sampletones_core.instructions`.

Reconstruction is a **search problem**. The input is cut into short, fixed-length
frames, and within each frame at most one instruction per channel is in effect. For
every frame the system must pick, from a large but finite catalog of NES
waveforms, the combination of instructions whose mixed output best matches that
slice of audio. Two ingredients define the system:

- a **criterion** that scores how well a candidate matches the target (§4), and
- a **selection strategy** that searches the catalog efficiently (§5).

Everything is compared in a perceptually-weighted **frequency** representation
rather than raw samples, because two sounds that are perceptually identical can
have very different waveforms depending on phase.

## 2. The pipeline

`Reconstructor` (`sampletones_core.reconstructions.reconstructor`) carries the
input through a fixed sequence of stages:

1. **Load** the audio (`sampletones_core.audio`) — mix to mono, resample, and
   optionally clean it up (normalize, quantize). Several sources load together, so
   one scale drawn from the peak of their sum holds them at the balance they were
   captured in.
2. **Set a working level** — scale the whole signal so its typical loudness sits in
   the range the NES channels can reproduce, keeping quiet passages matchable (§3.4).
3. **Fragment** it into short, fixed-length frames
   (`sampletones_core.fft.fragment`); from here on each channel holds one
   instruction per frame.
4. **Describe each frame** by a spectral feature that captures its frequency
   content (§3).
5. **Assign** every frame's channels to the sources, and with each channel the
   candidates it may sound there, each source judged against its own audio by the
   criterion (§5 and §4).
6. **Decode** each channel's stream, reading its candidates across the whole
   recording (§5).
7. **Refine** each chosen note onto the divider the recording's own fundamental stands at (§6).
8. **Render** the chosen instructions back into audio through the generators,
   keeping each oscillator continuous across frames.
9. **Reassemble** the channels into the final approximation and package it, with the
   instruction streams, as a `Reconstruction`.

Stages 3–7 are where the algorithms described below live; the rest is preparation
and playback.

A run says which of these it is in as it passes through them, so a reader watching a
conversion sees it move rather than waiting for the file. `ReconstructionStage` gathers
the eight steps into the four a reader is told apart — loading, matching, decoding,
rendering — and states the share each holds of the whole run;
[`progress.md`](../development/progress.md) describes how that account reaches the
screen from the worker process it is made in.

## 3. Representing a frame

### 3.1 The candidate catalog (library)

Before any reconstruction, `sampletones_core.library` precomputes a **library**: for
every possible instruction it renders the waveform its generator produces and stores
the corresponding spectral feature. Because NES waveforms are periodic, a
candidate's feature is computed as an average over many phase offsets, which makes
it essentially phase-independent — matching then compares spectral *shape* rather
than an accident of alignment. The library is keyed by the parameters that affect
it (sample rate, frame size, spectrum method, gamma, …) so a configuration change
produces a fresh library. See [Instruction library](instruction-library.md) for
the library as an artifact — how it is generated, explored and keyed.

### 3.2 Spectrum methods: FFT, log-FFT and CQT

The feature of a frame is a frequency *histogram* (`sampletones_core.structures`),
produced by one of three methods (`sampletones_core.fft.spectrum`,
configurable via `library.spectrum_method`):

| method   | frequency axis            | resolution                              | time support              |
|----------|---------------------------|-----------------------------------------|---------------------------|
| `fft`    | linear                    | uniform, `Δf ≈ sample_rate / N ≈ 27 Hz` | one short window (~37 ms) |
| `logfft` | logarithmic, floored at `Δf` | the FFT's `Δf`, on a musical axis     | one short window (~37 ms) |
| `cqt`    | logarithmic (constant-Q)  | constant *relative* (fine low end)      | long for low notes (~300 ms) |

They sit at different points of the **time–frequency trade-off** (the Gabor limit:
sharper frequency resolution requires a longer time window, and vice versa):

- **FFT** uses a window only slightly larger than one frame, so it localizes events
  sharply in time but resolves low frequencies coarsely — the lowest octave spans
  only a couple of bins. It is the simplest of the three.
- **log-FFT** takes the same FFT and *re-bins* its linear bins onto a logarithmic
  (musical) axis whose bin widths are floored at the FFT's `Δf`: the axis is linear
  where a musical interval falls below the resolution (roughly under 500 Hz at the
  defaults) and logarithmic above. Low tones therefore stay compact and every log
  bin aggregates whole FFT bins — the resolution is still the FFT's `Δf`, presented
  on a perceptual axis. Like the FFT it keeps a short window, so it localizes events
  sharply in time.
- **CQT** (constant-Q transform) places bins geometrically and gives
  every musical interval the same number of bins, so it resolves low pitches finely.
  It is the default.
  The price is time support: its low-frequency basis functions are long (hundreds of
  milliseconds), so brief events are smeared in time at the low end. _SampleToNES_
  computes the CQT **once over the whole signal** with a hop of one frame
  (`calculate_cqt_spectrum_columns`), so each frame's energy is reported at its own
  time position and the per-frame columns line up with the FFT path's frame centers.

The target and the library candidates are always described by the *same* method, so
their features are directly comparable bin by bin. All three methods share one scale
convention: a bin-centered tone of amplitude `A` contributes `A²/2` — its mean-square
power — to its bin, at every frame length (the analysis-window taper is compensated
by its energy gain).

### 3.3 The gamma transform

Whatever the method, the raw power spectrum is mapped into a "feature space" by a
Yeo-Johnson-family transform (`sampletones_core.fft.transformer`) controlled by a
`transformation_gamma` in `[0, 100]`:

- `gamma = 0` → identity: the feature is the power spectrum (the default);
- `gamma = 100` → logarithmic: the feature is `log(1 + x/ε)`.

Intermediate values interpolate smoothly. Higher gamma compresses the dynamic range,
emphasizing quiet spectral detail relative to loud peaks. The transform is applied
identically to target and candidate features, so it re-weights the comparison rather
than changing what is represented.

### 3.4 The working level (coefficient)

A single **coefficient** scales the input before matching so that its typical
loudness lands in the amplitude range the NES channels span. It anchors to a
*robust* level — a high percentile of the per-frame peak amplitudes over the audible
frames (`active_frame_level` in `sampletones_core.audio`) — rather than to the single
loudest sample. Anchoring to the peak would let one transient (a kick, a click)
push the rest of the signal below the quietest note the hardware can play, leaving
most frames un-matchable; anchoring to a robust level keeps the bulk of the signal
within reach while a lone transient simply saturates to the loudest available note.

## 4. Scoring a candidate: the criterion

`Criterion` (`sampletones_core.reconstructions.criterion`) scores a candidate
against the target frame as a weighted sum of a spectral and a temporal term:

```
cost = α · spectral + β · temporal          (default α = 0.8, β = 0.2)
```

- **spectral** compares the two frequency features with a perceptually-weighted
  distance, normalized by the target's own energy so the score is about *shape*. The
  per-bin distance is configurable — squared error, absolute error, or (the default)
  a **β-divergence** (a Kullback–Leibler-style measure that, for partials above the
  spectral floor, penalizes leaving target energy uncovered more strongly than adding
  energy beyond it). Bins are weighted by their span in auditory critical bands (the
  ERB scale) times the K-weighting loudness curve (ITU-R BS.1770), so each bin counts
  in proportion to the hearing resolution and loudness contribution it represents.
- **temporal** is the RMS difference between the target *waveform* and the candidate
  rendered at its best phase against the target, normalized by the target frame's own
  level. Evaluating it at the aligned phase makes it measure waveform *shape* — a
  property the magnitude spectrum discards — while keeping the spectral/temporal
  blend stable across frame loudness.

A lower cost is a better match. The criterion evaluates many candidates at once and,
on machines with a GPU, runs on the array backend in `sampletones_shared`.

## 5. Choosing instructions

Two questions settle what a frame plays, and each has its own owner. **Ownership** —
which channel a source holds this frame — is answered by the assignment in
`sampletones_core.reconstructions.reconstructor.stems.assignment`. **The stream** —
what a channel plays across the frames it holds — is answered by a decoder in
`sampletones_core.reconstructions.reconstructor.decoder`, named by
`generation.decoder.selector`. Both work from the same candidate scoring
(`reconstructor/matching.py`), the same criterion and the same library.

The assignment leaves every channel in play a **column** per frame: the candidates
that channel may sound there, best first. The decoder reads those columns into one
candidate per frame. Each decoder states how wide a column it reads, and the
assignment builds columns to exactly that width.

Candidates are scored in two stages: every candidate is first ranked by the
phase-independent spectral term, and the best `top_k` are then re-scored with the
full criterion, whose temporal term is evaluated on the candidate aligned to the
target (`find_best_phase`). The aligned phase stands in for the rendered phase,
which keeps each oscillator continuous across frames.

### 5.1 Assigning channels

A frame is assigned one pick at a time:

```
free = {channels the setup covers}
residual[source] = that source's own frame, for every source that sounds in it
while a source may still take a channel and free is non-empty:
    pick the single (source, channel, instruction) covering the most of
        residual[source], across every channel that source may still take
    subtract its rendered contribution from residual[source]
    assign it and remove that channel from `free`
```

Every pick lets whichever channel fits that source's residual best go first. Where
several channels share one generator kind, the lowest free channel of that kind
represents it during scoring, so successive picks over one kind land on the lowest free
channel. A channel still free when the picks end **rests**: it holds its channel's null
instruction for that frame, which is what keeps every channel's stream in step with
the frames it describes.

A source takes a channel in the frames its own audio reaches a level a channel can
render, and stands aside in the rest, so a frame it is silent in leaves its channels
resting.

A classic single-file conversion is one source covering every enabled channel, so the
one residual is the frame itself and the loop assigns every channel in each frame the
source sounds in. Several sources, a precedence hierarchy and a per-source channel cap
are the general case, described in [Stems reconstruction](stems.md); there each residual
holds one source's own sound, which is what makes the channel a source wins carry that
source's material.

### 5.2 Greedy decoding

The greedy decoder plays each frame's best candidate, reading one candidate per
column. Each frame is then decided by its own cost alone, which is fast and
straightforward, and the instruction streams follow each frame's match wherever it
leads — audible as jitter even where every individual frame is well matched.

### 5.3 Viterbi decoding

The Viterbi decoder weighs a frame's candidates against the frames around them. It
reads `top_k` candidates per column, forming a lattice of states over time, and
finds, per channel, the lowest-cost **path** through that lattice, where the path
cost combines:

- the per-frame **match cost** (the criterion, as an emission cost), and
- a **transition cost** between consecutive frames that grows with what changes
  between two instructions — turning a channel on or off, and changing pitch, volume
  or timbre.

Minimizing emission plus transition costs (the classic Viterbi dynamic program)
yields instruction streams that track the audio while changing only when the
improvement in match quality outweighs the cost of the change. The result is smoother
and more musical than the greedy output. It is the default.

A resting frame reaches the decoder as a column of one, so a channel that no source
took sits in the path as the off state it is, and coming back on costs what any other
on/off change costs.

## 6. Refining the pitch

The catalog is built on the equal-tempered grid, so the matching can place a frame no closer than
the nearest semitone. The hardware is finer than that: a note reaches a channel as an 11-bit
divider, and one step of that divider spans **0.85 cents at A-0, 4 cents at C-3, 16 cents at C-5**,
reaching a whole semitone only around C-7, where the divider grid and the note grid meet. Everything
below that is room the matching leaves unused, and material that was never in A=440 equal
temperament — most recordings of most instruments — sits somewhere inside it.

`sampletones_core.reconstructions.reconstructor.refinement` spends that room, after the decoder has
settled which note each frame plays and before the frames are rendered. It spends it where the run
asks: a stem entry names the channels it carries towards its own recording, so one recording's bass
line can land on its exact tuning while another's lead keeps the grid.

### 6.1 Reading rather than searching

The refinement does not search. Two measurements settle why:

- Against a **matched** candidate the criterion answers a detune smoothly and monotonically — a
  25-cent error costs about 0.09 where a 50-cent error costs about 0.40. Against a **realistic**
  target, where the candidate cannot match the timbre, that response is a small ripple on a
  timbre-dominated floor with many local minima, and taking the lowest-cost divider over a sweep
  lands 15–30 cents from the truth.
- Searching also costs what the library exists to avoid. Scoring one extra candidate per frame
  means rendering it and extracting its feature, which measures around **2.1 s per second of
  audio** — more than a whole conversion of the same audio.

So the answer is read out of the transform instead. `sampletones_core.fft.instantaneous` takes the
**phase** the constant-Q transform already computes and `calculate_cqt_spectrum_columns` discards.
A partial standing between two bin centers still advances its phase at its own rate, so comparing
that advance across two columns against the rate the bin itself turns at states the partial's
frequency far more finely than the bins are spaced. Reading the first few harmonics of the note the
decoder chose, each weighted by the energy behind it and each settled against the fundamental the
harmonics below it agreed on, places the note **within a tenth of a cent** across the whole range.

The reading also states how much of the frame stands behind it — the share of the column's energy
its harmonics hold. A pitched frame reads around 0.5, a frame sharing the channel with another tone
around 0.3, and noise around 0.04, so one threshold separates the frames worth bending from the
frames with no pitch to read.

### 6.2 Landing the note, and holding it

A reading becomes a bend through the generator, which owns the divider geometry: `bend_towards`
answers with the divider steps that land the note nearest the frequency read, bounded by
`bend_range` — **half the gap to each neighboring note**. That bound is what leaves the refined
pitches gapless: note *n* covers `[(tₙ + tₙ₊₁) / 2, (tₙ + tₙ₋₁) / 2]`, and those windows tile the
divider range exactly, so every divider the notes span is reachable and none is claimed twice.

A bend that followed every reading exactly would jitter, and jitter is more audible than the tuning
it chases. So the per-frame proposals are settled by a change-penalized walk, the same shape the
Viterbi decoder settles a note contour with: the cost of a bend is how far it stands from that
frame's reading, plus a toll on changing at all. The states a frame may take are the bends its
neighborhood proposed together with no bend, which keeps the walk to a handful of states even where
a note owns tens of dividers.

### 6.3 What it costs, and what it leaves alone

The refinement enumerates no candidate, rescores nothing, and leaves the library, the per-frame
matching and the decoder's lattice exactly as they were. What it adds is one transform per
recording and a small walk per channel.

What that transform costs depends on the machine, and the spread is wide: on a CUDA build it
disappears into the noise, while on a CPU build it is a measurable share of a short conversion —
a tenth or more, since the reading needs a handful of bins per frame and the transform computes
every bin the spectrum covers. Restricting it to the bins the chosen notes actually name is the
work `docs/development/bugs-and-todos.md` records under **Features**.

A frame makes no proposal where it rests, where the stem holding it leaves that channel out, where
its channel is not pitched — the noise channel's sixteen periods have no finer grid — or where its
reading falls below the confidence threshold. A conversion that bent no note records both bend
dimensions as ones the channel governs, so it writes the instrument an unrefined run writes.

Which recordings are carried, and on which channels, each stem entry states for itself in
`bends` — a subset of the channels it occupies, and of the three that load a divider. A channel a
stem leaves out keeps the note the matching chose, and a stem carrying nothing at all is never
read, so the transform is spent only where a bend comes of it. The settings below shape a bend
once it is asked for, and hold for a whole run.

| parameter | default | notes |
|---|---|---|
| `generation.refinement.confidence` | 0.15 | the share of a frame's energy its harmonics must hold |
| `generation.refinement.change_weight` | 2.0 | divider steps of reading error worth avoiding one change |
| `generation.refinement.window` | 4 | the frames on either side whose readings a frame may settle on |

## 7. Rendering and reassembly

Once instructions are chosen, each one is rendered back through its generator
(`sampletones_core.generators`), which carries oscillator phase across frames so
there are no clicks at frame boundaries; an "off" instruction yields silence for that
channel and frame. The per-channel renderings are concatenated and summed into the
final approximation, and the `Reconstruction` keeps both the audio and the
per-channel instruction streams (which can be exported to a tracker format via
`sampletones_core.exporters`). The coefficient from §3.4 is stored so the
reconstruction and the original can be shown and played on a common scale.

## 8. Limitations

- **Dynamic range.** A single NES tonal channel spans roughly 25 dB from its
  quietest to its loudest note, and the coefficient is one global scalar. Material
  whose *useful* content spans a wider range than that (a long crescendo, a very
  quiet passage under a loud one) cannot be fully captured: content far below the
  working level falls under the quietest playable note and is rendered as silence.
- **CQT time resolution.** Because constant-Q analysis needs long windows at low
  frequencies, low-pitched transients are inherently smeared in time under `cqt`;
  `fft`/`logfft` localize time better at the cost of low-frequency resolution.
- **Per-channel independence in Viterbi.** Channels are decoded independently once the
  assignment has settled their columns, which is fast but not jointly optimal across
  channels.
- **Refinement needs a fundamental to read.** A frame carrying several pitches at once, or one
  whose sound is unpitched, states no fundamental for its channel and keeps the note the matching
  chose. The room a bend has also closes with pitch: a divider step is a whole semitone from around
  C-7 up, so notes there sound where the grid puts them.

## Appendix — key parameters and where things live

Default configuration (44.1 kHz, 60 Hz change rate, channels pulse 1 + triangle +
noise):

| parameter                | default | notes                                              |
|--------------------------|---------|----------------------------------------------------|
| frame length             | 735     | `sample_rate / nes_frequency`, ~17 ms              |
| spectrum method          | `cqt`   | `fft` / `logfft` / `cqt`                            |
| `transformation_gamma`   | 0       | 0 = power spectrum, 100 = log                       |
| spectral / temporal weight | 0.8 / 0.2 | criterion blend                                 |
| spectral distance        | β-divergence | also `squared`, `absolute`                     |
| selector                 | Viterbi | `greedy` / `viterbi`                                |
| pitch refinement         | per stem | bends each note onto the divider the source sounds  |
| normalize / quantize     | on / off | input preprocessing                                |

Package map:

| concern                         | package                                              |
|---------------------------------|------------------------------------------------------|
| NES channel models              | `sampletones_core.generators`                        |
| instruction value types         | `sampletones_core.instructions`                      |
| windowing, spectra, features    | `sampletones_core.fft`                               |
| candidate catalog             | `sampletones_core.library`                           |
| scoring                         | `sampletones_core.reconstructions.criterion`         |
| selection + assembly            | `sampletones_core.reconstructions.reconstructor`     |
| audio I/O and level             | `sampletones_core.audio`                             |
| tracker export                  | `sampletones_core.exporters`                         |
| pitch refinement                | `sampletones_core.reconstructions.reconstructor.refinement` |
| criterion calibration           | `sampletones_core.calibration`                       |
| analytic waveform synthesis     | `sampletones_synthesis`                              |
