# Reconstruction algorithms

This document explains how _SampleToNES_ turns an audio sample into a *reconstruction*: a sequence of NES
instructions that approximates the original when it plays on the console's sound hardware. Read it to see
how a frame's sound is described, scored and chosen, and where each setting acts.

The tunable choices described here are set empirically. [Calibration](../tools/calibration.md) describes
the experiment that sets them.

## 1. The problem

The NES sound chip ([Ricoh 2A03 APU](../glossary.md#2a03-apu)) produces a few simple, fixed waveforms
across four usable channels:

- two [**pulse**](../glossary.md#pulse-square) (square) channels, each with 4
  [duty cycles](../glossary.md#duty-cycle) and 15 volume levels;
- one [**triangle**](../glossary.md#triangle) channel of fixed shape and amplitude, with pitch only;
- one [**noise**](../glossary.md#noise) channel: a pseudo-random [LFSR](../glossary.md#lfsr) generator
  with 16 periods, 15 volume levels and a short/long mode.

A program steers these channels by issuing *instructions* at the
[NES frequency](../glossary.md#nes-frequency), for example *pulse 1: note A-4, volume 12, 50 % duty*.
Approximating an arbitrary sound this way produces a **reconstruction**: one instruction stream per
channel whose mixed, rendered output resembles the input as closely as the hardware permits. By default a
reconstruction uses one pulse channel, the triangle and the noise. The second pulse can be switched on
when a recording's channels are chosen.

Reconstruction is a **search problem**. The input is cut into short, fixed-length frames, and within each
frame at most one instruction per channel is in effect. For every frame the system must pick, from a large
but finite catalog of NES waveforms, the combination of instructions whose mixed output best matches that
slice of audio. Two ingredients define the system:

- a **criterion** that scores how well a candidate matches the target
  ([section 4](#4-scoring-a-candidate-the-criterion)), and
- a **selection strategy** that searches the catalog efficiently ([section 5](#5-choosing-instructions)).

Everything is compared in a perceptually weighted **frequency** representation instead of raw samples,
because two sounds that are perceptually identical can have very different waveforms depending on phase.

## 2. The pipeline

A reconstruction runs through a fixed sequence of stages:

1. **Load** the audio: mix to mono, resample, and optionally clean it up (normalize, quantize). Several
   sources load together, so one scale drawn from the peak of their sum keeps them at the balance they
   were captured in. The reconstruction records that scale.
2. **Set a working level.** Scale the whole signal so its typical frame plays at the level one channel
   renders at full volume, which keeps quiet passages matchable
   ([section 3.4](#34-the-working-level-coefficient)).
3. **Fragment** the signal into short, fixed-length frames. From here on each channel has one instruction
   per frame.
4. **Describe each frame** by a spectral feature that captures its frequency content
   ([section 3](#3-representing-a-frame)).
5. **Assign** every frame's channels to the sources. Each channel also gets the candidates it may sound
   there, and each source is judged against its own audio by the criterion
   ([section 5](#5-choosing-instructions) and [section 4](#4-scoring-a-candidate-the-criterion)).
6. **Decode** each channel's stream, reading its candidates across the whole recording
   ([section 5](#5-choosing-instructions)).
7. **Refine** each chosen note onto the [divider](../glossary.md#divider) the recording's own fundamental
   stands at ([section 6](#6-refining-the-pitch)).
8. **Render** the chosen instructions back into audio through the generators, keeping each oscillator
   continuous across frames.
9. **Reassemble** the channels into the final approximation, and save it with the instruction streams as
   a reconstruction.

Stages 3–7 are where the algorithms described below live. The rest is preparation and playback.

## 3. Representing a frame

### 3.1 The candidate catalog (library)

Before any reconstruction, the program precomputes a **library**. For every possible instruction it
renders the waveform that instruction produces and stores the corresponding spectral feature. NES
waveforms are periodic, so a candidate's feature is computed from its power spectrum averaged over many
phase offsets. That makes it essentially phase-independent, and matching compares spectral *shape* and
not an accident of alignment. The library is keyed by the parameters that affect it (sample rate, frame
size, spectrum method, gamma, …), so a configuration change produces a fresh library. See
[Instruction library](instruction-library.md) for how it is generated and keyed.

### 3.2 Spectrum methods: FFT, log-FFT and CQT

The feature of a frame is a frequency *histogram*, produced by one of three methods
(`library.spectrum_method`). The figures below are for 44.1 kHz audio at a 60 Hz change
rate:

| method   | frequency axis            | resolution                              | time support              |
|----------|---------------------------|-----------------------------------------|---------------------------|
| `fft`    | linear                    | uniform, `Δf ≈ sample_rate / N ≈ 27 Hz` | one short window (~37 ms) |
| `logfft` | logarithmic, floored at `Δf` | the FFT's `Δf`, on a musical axis     | one short window (~37 ms) |
| `cqt`    | logarithmic (constant-Q)  | constant *relative* (fine low end)      | long for low notes (~600 ms) |

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
  It is the default. Its lowest bin sits at the lowest note the chip sounds: the
  triangle's, an octave below the pulse's, since the triangle steps through its wave
  at half the pulse's rate. A bass line on the triangle is therefore read from its
  fundamental, which is where the pitch of a bent note is read from too.
  Bins above the pulse's lowest note are identical at either floor. The lower floor adds the
  triangle's lowest octave, which a triangle bass needs, at the cost of conversion time and a larger
  library.
  The price is time support: its low-frequency basis functions are long (hundreds of
  milliseconds), so brief events are smeared in time at the low end. _SampleToNES_
  computes the CQT **once over the whole signal** with a hop of one frame, so each
  frame's energy is reported at its own time position and the per-frame columns line up
  with the FFT path's frame centers.

The target and the library candidates are always described by the *same* method, so
their features are directly comparable bin by bin. All three methods share one scale
convention: a bin-centered tone of amplitude `A` contributes `A²/2` — its mean-square
power — to its bin, at every frame length (the analysis-window taper is compensated
by its energy gain).

### 3.3 The gamma transform

Whatever the method, the raw power spectrum is mapped into a "feature space" by a
Yeo-Johnson-family transform controlled by a
`transformation_gamma` in `[0, 100]`:

- `gamma = 0` → identity: the feature is the power spectrum (the default);
- `gamma = 100` → logarithmic: the feature is `log(1 + x/ε)`.

Intermediate values interpolate smoothly. Higher gamma compresses the dynamic range,
emphasizing quiet spectral detail relative to loud peaks. The transform is applied
identically to target and candidate features, so it re-weights the comparison rather
than changing what is represented. Arithmetic on features — a library candidate's
average over phases, the mix of a frame's picks — is carried out on the power spectra
they describe and transformed afterward, so its result is the feature of that power
at every gamma.

### 3.4 The working level (coefficient)

A single **coefficient** scales the input before matching, so its typical frame plays at the level one
channel renders at full volume. The typical frame is a *robust* level: a high percentile of the per-frame
RMS levels over the audible frames. A lone transient such as a kick or a click therefore saturates to the
loudest available note, while the bulk of the signal stays within reach of the quietest one. RMS measures
how much sound a frame carries. A channel's volume renders that quantity, whatever the waveform's crest.

That level is brought to the full-scale RMS level of the quietest tone channel the setup covers. This is
the triangle, whose RMS level is its peak over √3. A pulse, which swings between two levels, takes over
when no triangle is covered, and the noise channel does for a noise-only setup. A steady tone then lands at
what a single tone channel renders whole, so one channel can answer it, and louder frames call on more
channels.

## 4. Scoring a candidate: the criterion

The **criterion** scores a candidate against the target frame as a weighted sum of a spectral and a
temporal term:

```
cost = α · spectral + β · temporal
```

α and β are the `spectral_loss_weight` and `temporal_loss_weight` settings.

- **spectral** compares the two frequency features with a perceptually weighted distance. The distance is
  normalized by the target's own energy, so the score is about *shape*. The per-bin distance is
  configurable: squared error, absolute error, or a **β-divergence**, which is the default. A
  β-divergence is a Kullback–Leibler-style measure that penalizes leaving target energy uncovered more
  strongly than adding energy beyond it.

  Both sides are measured above a floor set under the frame's loudest bin by the configured dynamic range
  (`generation.metric.dynamic_range_decibels`). An addition therefore costs what it adds wherever it stays
  audible beside what the frame sounds, such as quiet noise under a loud tone. A frame of noise costs what
  a channel leaves out of it. A frame quieter than `generation.metric.silence_floor` is measured from that
  level, which keeps a silent frame's score finite.

  Bins are weighted by their span in auditory critical bands (the ERB scale) times the K-weighting
  loudness curve (ITU-R BS.1770). Each bin then counts in proportion to the hearing resolution and
  loudness contribution it represents.
- **temporal** measures the target *waveform* against what the frame's channels are expected to render. It
  is normalized by the target frame's own level, so the spectral/temporal blend holds across frame
  loudness. A candidate whose frames repeat one waveform shape (a note, or noise whose register cycle fits
  inside a frame) renders its waveform at its best phase against what the other channels leave of the
  target. That makes the term measure waveform *shape*, a property the magnitude spectrum discards. A
  candidate whose frames show different stretches of a pseudo-random sequence renders its mean level with
  a spread about it. For waveforms expected to sum to `E` with a per-sample variance `V`,
  `E mean((t − x)²) = mean((t − E)²) + V`, whose root normalizes as above.

A lower cost is a better match. The criterion scores many candidates at once, and runs on the graphics
card where the machine has one.

## 5. Choosing instructions

Two questions settle what a frame plays. Each is answered separately.

- **Ownership**: which channels a source holds in this frame. The assignment
  ([section 5.1](#51-assigning-channels)) answers it.
- **The stream**: what a channel plays across the frames it holds. A decoder answers it, and the
  `generation.decoder.selector` setting chooses the decoder.

Both work from the same candidate scoring, the same criterion and the same library.

A **source** is one recording in the conversion, a [stem](../glossary.md#stem). A conversion from a single
file has one source. A [pick](../glossary.md#pick), a [mix](../glossary.md#mix) and a [column](../glossary.md#column) are
defined in the glossary.

The assignment leaves every channel in play a column per frame. The decoder reads those columns into one
candidate per frame. Each decoder says how wide a column it reads, and the assignment builds columns to
exactly that width.

A candidate is scored by the frame's cost with it sounding beside the picks its source already holds in
that frame. The channel's silence is always among the candidates. The picks add up to a mix: their
phase-averaged power spectra add, and so do the waveforms they are expected to render and their variances.

Scoring runs in two stages. First, every candidate of one channel's kind is added to the mix and ranked by
the phase-independent spectral term. Then the best `top_k`, together with the kind's silence, are
re-scored with the full criterion.

A candidate whose frames repeat one shape adds its waveform. With `find_best_phase` on, the waveform is
aligned to what the mix leaves of the target. Otherwise the candidate's library sample is added from its
start. Either phase stands in for the one the generator reaches when the frame is rendered. A candidate
whose frames show different stretches of a sequence renders whatever stretch its channel has reached. It
therefore adds its mean level and its variance, whatever `find_best_phase` says.

The scored candidates form the channel's column, best first, with silence ahead of an equal cost. `top_k`
sets how many of them a wide decoder reads.

### 5.1 Assigning channels

A frame is assigned one pick at a time, for as long as a source may still take a channel and a pick lowers
a frame's cost. Each round takes the (source, channel) pair whose best candidate lowers its source's cost
the most, weighted by the energy of the source's frame, and adds that candidate to the source's mix.

When the picks end, every channel still free goes to the first sounding source that may hold it, headed by
silence. Then every held channel is scored once more with its source's other channels sounding. That last
pass lets a channel taken early fall silent where the later channels cover its sound, or sound where they
leave room.

A frame one channel renders whole therefore sounds one channel. Once the triangle covers a sine, adding a
pulse or the noise raises the cost, and those channels hold their silence.

A channel no pick took keeps its column, headed by its silence, so the decoder may still sound it where
the frames around ask for it. It counts against its source's count, so no decoded frame sounds more
channels than that count.

A channel no source may hold is [**resting**](../glossary.md#resting). It plays its channel's null
instruction for that frame, which keeps every channel's stream in step with the frames it describes.

A classic single-file conversion is one source covering every enabled channel. The one mix answers the
frame itself, and every channel in each frame the source sounds in is held, sounding or silent. Several
sources, a precedence hierarchy, a [drive](../glossary.md#drive) per source channel and a per-source
count of channels sounding at once are the general case, described in [Stems reconstruction](stems.md).
There each mix answers one source's own sound, so the channel a source wins carries that source's
material.

### 5.2 Greedy decoding

The greedy decoder plays each frame's best candidate, reading one candidate per column. Each frame is
decided by its own cost alone, which is fast and simple. The instruction streams follow each frame's match
wherever it leads. That is audible as jitter even where every individual frame is well matched.

### 5.3 Viterbi decoding

The Viterbi decoder weighs a frame's candidates against the frames around them. It reads `top_k`
candidates per column, with the channel's silence among them, and forms a lattice of states over time. Per
channel, it finds the lowest-cost **path** through the lattice. The path cost combines:

- the per-frame **match cost** (the criterion, as an emission cost), and
- a **transition cost** between consecutive frames that grows with what changes between two instructions:
  turning a channel on or off, and changing pitch, volume or timbre.

Minimizing emission plus transition costs (the classic Viterbi dynamic program) yields instruction
streams that track the audio while changing only when the improvement in match quality outweighs the cost
of the change. The result is smoother and more musical than the greedy output. It is the default.

A resting frame reaches the decoder as a column of one, so a channel that no source took sits in the path
as the off state it is. Coming back on costs what any other on/off change costs. A frame the decoder
settles on a silent instruction is released to the resting stem, so the resting stem id and the silence
name the same frames. A channel decoded silent throughout is [standing by](../glossary.md#standing-by).

## 6. Refining the pitch

The catalog is built on the equal-tempered grid, so the matching places a frame no closer than the nearest
semitone. The hardware is finer: a note reaches a channel as an 11-bit [divider](../glossary.md#divider).
One step of that divider spans **0.85 cents at A-0, 4 cents at C-3 and 16 cents at C-5**. It reaches a
whole semitone only around C-7, where the divider grid and the note grid meet. Everything below that is
room the matching leaves unused. Material that was never in A=440 equal temperament, which is most
recordings of most instruments, sits somewhere inside it.

The **refinement** uses that room. It runs after the decoder has settled which note each frame plays and
before the frames are rendered. It works where the run asks: a stem entry names the channels it carries
toward its own recording, so one recording's bass line can land on its exact tuning while another's lead
keeps the grid.

### 6.1 Reading rather than searching

The refinement reads the pitch out of the recording. Searching for it fails on two counts. Against a
target whose timbre the candidate cannot match, the criterion answers a detune with a ripple of local
minima, so the lowest-cost divider lands far from the truth. And scoring an extra candidate per frame
costs the rendering and feature extraction the library exists to avoid.

The reading comes from the transform instead, from the **phase** the constant-Q transform already computes
and the spectrum discards. A partial standing between two bin centers still advances its phase at its own
rate. Comparing that advance across two columns against the rate the bin itself turns at gives the
partial's frequency far more finely than the bins are spaced. The reading takes the first few harmonics of
the note the decoder chose. It weights each by the energy behind it and settles each against the
fundamental the harmonics below it agreed on. A harmonic counts where its partial stands within half a
semitone of where that fundamental puts it, the room a note owns, so a partial another voice sounds a bin
away stays out of the reading. The advance across two columns repeats every `sample_rate / hop` hertz
(60 Hz at the defaults), which from about 1 kHz up is narrower than a note's room. There a second reading,
of the advance over a sixteenth of a hop, names the repeat the first harmonic stands on, and the advance
across two columns keeps its precision inside it. This places the note far more finely than a divider step across the whole range.

The reading also says how much of the frame stands behind it: the share of the column's energy its
harmonics hold, with every bin measured on the scale the features use. On that scale a bass takes the
share its level gives it in every register, so a melody over a low bass keeps its reading. One
threshold (`generation.refinement.confidence`) therefore separates the frames worth bending from the
frames with no pitch to read.

### 6.2 Landing the note, and holding it

A reading becomes a bend through the generator, which owns the divider geometry. The generator answers
with the divider steps that land the note nearest the frequency read, bounded to **half the gap to each
neighboring note**. That bound leaves the refined pitches gapless. Note *n* covers
`[(tₙ + tₙ₊₁) / 2, (tₙ + tₙ₋₁) / 2]`, and those windows tile the divider range exactly, so every divider the
notes span is reachable and none is claimed twice.

A bend that followed every reading exactly would jitter, and jitter is more audible than the tuning it
chases. The per-frame proposals are therefore settled by a change-penalized walk, the same shape the
Viterbi decoder uses to settle a note contour. The cost of a bend is how far it is from that frame's
reading, plus a toll on changing at all. The states a frame may take are the bends its neighborhood
proposed, together with no bend. That keeps the walk to a handful of states even where a note owns tens of
dividers. A bend counts divider steps from its own note, so each note's frames are settled on their own: a
frame that reads nothing keeps a bend its own note read, and a new note starts from its own reading.

A frame makes no proposal where it rests, where the stem holding it leaves that channel out, where its
channel is not pitched (the noise channel's sixteen periods have no finer grid), or where its reading
falls below the confidence threshold. A conversion that bent no note records both bend dimensions as ones
the channel governs, so it writes the instrument an unrefined run writes.

Each stem entry says which recordings are carried, and on which channels, in `bends`: a subset of the
channels it occupies, and of the three that load a divider. A channel a stem leaves out keeps the note the
matching chose. A stem carrying nothing at all is never read, so the transform is spent only where a bend
comes of it.

The settings under `generation.refinement` shape a bend once it is asked for: `confidence`,
`change_weight` and `window`. They hold for a whole run. [The configuration file](../formats/configuration.md)
lists them.

## 7. Rendering and reassembly

A reconstruction is its instruction streams. Each stream is rendered back through the channel that plays
it, as it stands. The channel carries the oscillator's phase across frames, so frame boundaries make no
clicks, and resets it on a new note where the settings say so. An "off" instruction gives silence for that
channel and frame. The per-channel renderings are summed into the final approximation.

The audio is rendered on demand, so what a reconstruction shows is what an export plays. A `.stn`
therefore holds the instructions, the per-frame ownership and the setup they were chosen under, which is
far smaller than the audio would be. The working level from
[section 3.4](#34-the-working-level-coefficient) is stored too, so the reconstruction and the original can
be shown and played on a common scale.

## 8. Limitations

- **Dynamic range.** A single NES tonal channel spans a limited range from its quietest to its loudest note,
  and the coefficient is one global scalar. Material whose *useful* content spans a wider range than that
  cannot be fully captured. A long crescendo and a very quiet passage under a loud one are examples.
  Content far below the working level falls under the quietest playable note and is rendered as silence.
- **The triangle's fixed level.** The triangle plays at one volume. A bass quieter than that level is left
  out, and a bass near it is played.
- **CQT time resolution.** Constant-Q analysis needs long windows at low frequencies, so low-pitched
  transients are smeared in time under `cqt`. `fft` and `logfft` localize time better at the cost of
  low-frequency resolution.
- **Per-channel independence in Viterbi.** Channels are decoded independently once the assignment has
  settled their columns. That is fast but not jointly optimal across channels.
- **Refinement needs a fundamental to read.** A frame carrying several pitches at once, or one whose sound
  is unpitched, has no fundamental for its channel and keeps the note the matching chose. The room a bend
  has also closes with pitch: a divider step is a whole semitone from around C-7 up, so notes there sound
  where the grid puts them.
