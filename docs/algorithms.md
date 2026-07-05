# Reconstruction algorithms

This document explains how SampleToNES turns an arbitrary audio sample into a
*reconstruction* — a sequence of NES instructions that, when played back on the
console's sound hardware, approximates the original. It is written to be readable
without prior knowledge of the codebase, while pointing at the packages that
implement each part.

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
every frame the system must pick, from a large but finite catalogue of NES
waveforms, the combination of instructions whose mixed output best matches that
slice of audio. Two ingredients define the system:

- a **criterion** that scores how well a candidate matches the target (§4), and
- a **selection strategy** that searches the catalogue efficiently (§5).

Everything is compared in a perceptually-weighted **frequency** representation
rather than raw samples, because two sounds that are perceptually identical can
have very different waveforms depending on phase.

## 2. The pipeline

`Reconstructor` (`sampletones_core.reconstructions.reconstructor`) carries the
input through a fixed sequence of stages:

1. **Load** the audio (`sampletones_core.audio`) — mix to mono, resample, and
   optionally clean it up (normalize, quantize).
2. **Set a working level** — scale the whole signal so its typical loudness sits in
   the range the NES channels can reproduce, keeping quiet passages matchable (§3.4).
3. **Fragment** it into short, fixed-length frames
   (`sampletones_core.fft.fragment`); from here on each channel holds one
   instruction per frame.
4. **Describe each frame** by a spectral feature that captures its frequency
   content (§3).
5. **Select** the instructions — for every frame and channel, pick the candidate
   that best matches, judged by the criterion (§5 and §4).
6. **Render** the chosen instructions back into audio through the generators,
   keeping each oscillator continuous across frames.
7. **Reassemble** the channels into the final approximation and package it, with the
   instruction streams, as a `Reconstruction`.

Stages 3–5 are where the algorithms described below live; the rest is preparation
and playback.

## 3. Representing a frame

### 3.1 The candidate catalogue (library)

Before any reconstruction, `sampletones_core.library` precomputes a **library**: for
every possible instruction it renders the waveform its generator produces and stores
the corresponding spectral feature. Because NES waveforms are periodic, a
candidate's feature is computed as an average over many phase offsets, which makes
it essentially phase-independent — matching then compares spectral *shape* rather
than an accident of alignment. The library is keyed by the parameters that affect
it (sample rate, frame size, spectrum method, gamma, …) so a configuration change
produces a fresh library.

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
  milliseconds), so brief events are smeared in time at the low end. SampleToNES
  computes the CQT **once over the whole signal** with a hop of one frame
  (`calculate_cqt_spectrum_columns`), so each frame's energy is reported at its own
  time position and the per-frame columns line up with the FFT path's frame centres.

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

Both selectors live in `sampletones_core.reconstructions.reconstructor.selector` and
are chosen with `generation.decoder.selector`. They share the criterion and the
library; they differ only in how they search.

Both score candidates in two stages: every candidate is first ranked by the
phase-independent spectral term, and the best `top_k` are then re-scored with the
full criterion, whose temporal term is evaluated on the candidate aligned to the
target (`find_best_phase`). The aligned phase stands in for the rendered phase,
which keeps each oscillator continuous across frames.

### 5.1 Greedy (per-frame)

The greedy selector — shipped in 0.2.3 and still available — treats every frame
independently:

```
remaining = {enabled channels}
while remaining:
    pick the single (channel, instruction) with the lowest cost
        across all candidates of all remaining channels
    subtract its rendered contribution from the frame's residual
    assign it and remove that channel from `remaining`
```

It assigns each channel exactly once per frame, always letting the channel that fits
the residual best go first. It is simple and fast, but it has **no memory between
frames**: nothing discourages the instruction streams from jumping around frame to
frame, which can sound jittery even when each individual frame is well matched.

### 5.2 Viterbi (continuity-aware)

The Viterbi selector adds temporal continuity. For each frame it keeps the *top-k*
lowest-cost candidates per channel, forming a lattice of states over time. It then
finds, per channel, the lowest-cost **path** through that lattice, where the path
cost combines:

- the per-frame **match cost** (the criterion, as an emission cost), and
- a **transition cost** between consecutive frames that penalizes discontinuity —
  switching a channel on or off, and changing pitch, volume or timbre.

Minimizing emission plus transition costs (the classic Viterbi dynamic program)
yields instruction streams that track the audio while changing only when the
improvement in match quality outweighs the cost of the change. The result is
smoother and more musical than the greedy output. It is the default.

## 6. Rendering and reassembly

Once instructions are chosen, each one is rendered back through its generator
(`sampletones_core.generators`), which carries oscillator phase across frames so
there are no clicks at frame boundaries; an "off" instruction yields silence for that
channel and frame. The per-channel renderings are concatenated and summed into the
final approximation, and the `Reconstruction` keeps both the audio and the
per-channel instruction streams (which can be exported to a tracker format via
`sampletones_core.exporters`). The coefficient from §3.4 is stored so the
reconstruction and the original can be shown and played on a common scale.

## 7. Calibration

The criterion is full of tunable choices — the spectrum method, gamma, the
perceptual exponent on the loudness curve, the spectral/temporal blend, the
Viterbi transition weights — and their best values are an empirical question.
**Calibration** answers it with a repeatable experiment: reconstruct a fixed
probe corpus under several candidate configurations and let independent judges
score the results, so configuration decisions rest on measured quality and
targeted listening. The harness lives in `sampletones_core.calibration` and runs
as a script:

```
python scripts/calibration.py [--config <base>] [--methods fft,cqt]
    [--perceptual-exponents 0.5,1.0] [--temporal-weights 0.1,0.3]
```

It has three moving parts:

- **A synthetic corpus** (`calibration.corpus`) of short, deterministic probe
  signals in six categories: steady tones across the pitch range, pulse timbres
  of several duty cycles, white and dark noise, tone-plus-noise mixes,
  percussive transients (snare, kick, pluck) and a crescendo probing the dynamic
  range. Each category isolates one kind of decision the criterion must get
  right — pitch, timbre, noise balance, attack sharpness, level tracking — and
  the fixed seed makes every run bit-identical, so scores are comparable across
  runs and code changes.
- **Variants** (`calibration.runner`): the requested knob values are swept as a
  cartesian product over a base configuration, each combination becoming a
  labeled, complete configuration. Missing instruction libraries are generated
  on the fly. Every corpus item is reconstructed under every variant, and the
  approximation is compared against the preprocessed original on the common
  scale set by the working level (§3.4).
- **Referees** (`calibration.referee`): a referee is a full-reference audio
  distance — zero for identical signals, growing with audible difference.
  Referees judge in their own representation, independent of the criterion under
  test; an outside yardstick keeps the comparison honest when the criterion
  itself is what changes between variants. The built-in referee measures
  log-spectral distance over ERB-spaced bands at three STFT resolutions
  simultaneously, covering the time–frequency trade-off that the criterion
  resolves with a single frame length. Band energies are floored at a fixed
  audibility range below the reference's loudest band, so the score reflects
  audible content and holds steady under a common gain. Its tuning is a
  `RefereeConfig` loaded from `sampletones_config/calibration/referee.yaml`.
  When the [zimtohrli](https://github.com/google/zimtohrli) binary is installed
  it joins automatically as a second, psychoacoustic referee.

Each run writes a timestamped directory containing the corpus WAVs, `report.csv`
(one row per variant × item × referee) and `report.md` — a per-referee pivot
with one row per variant and one column per corpus category, plus the overall
mean. Lower scores mean closer reconstructions, and the numbers rank variants
relative to one another within a run. The built-in referee measures per-band
energy agreement, which makes it most reliable for timbre, noise-balance and
level questions; pitch accuracy is best arbitrated by the external referee or by
ear. The intended workflow is therefore: sweep, read the pivot, shortlist the
contenders, and listen to those.

## 8. Limitations

- **Dynamic range.** A single NES tonal channel spans roughly 25 dB from its
  quietest to its loudest note, and the coefficient is one global scalar. Material
  whose *useful* content spans a wider range than that (a long crescendo, a very
  quiet passage under a loud one) cannot be fully captured: content far below the
  working level falls under the quietest playable note and is rendered as silence.
- **CQT time resolution.** Because constant-Q analysis needs long windows at low
  frequencies, low-pitched transients are inherently smeared in time under `cqt`;
  `fft`/`logfft` localize time better at the cost of low-frequency resolution.
- **Per-channel independence in Viterbi.** Channels are decoded independently after a
  shared residual is formed, which is fast but not jointly optimal across channels.

## Appendix — key parameters and where things live

Default configuration (44.1 kHz, 30 Hz change rate, channels pulse 1 + triangle +
noise):

| parameter                | default | notes                                              |
|--------------------------|---------|----------------------------------------------------|
| frame length             | 1470    | `sample_rate / nes_frequency`, ~33 ms              |
| spectrum method          | `cqt`   | `fft` / `logfft` / `cqt`                            |
| `transformation_gamma`   | 0       | 0 = power spectrum, 100 = log                       |
| spectral / temporal weight | 0.8 / 0.2 | criterion blend                                 |
| spectral distance        | β-divergence | also `squared`, `absolute`                     |
| selector                 | Viterbi | `greedy` / `viterbi`                                |
| normalize / quantize     | on / off | input preprocessing                                |

Package map:

| concern                         | package                                              |
|---------------------------------|------------------------------------------------------|
| NES channel models              | `sampletones_core.generators`                        |
| instruction value types         | `sampletones_core.instructions`                      |
| windowing, spectra, features    | `sampletones_core.fft`                               |
| candidate catalogue             | `sampletones_core.library`                           |
| scoring                         | `sampletones_core.reconstructions.criterion`         |
| selection + assembly            | `sampletones_core.reconstructions.reconstructor`     |
| audio I/O and level             | `sampletones_core.audio`                             |
| tracker export                  | `sampletones_core.exporters`                         |
| criterion calibration           | `sampletones_core.calibration`                       |
