# Glossary

Recurring terms used across the documentation, grouped by area. Other documents
link here rather than redefining a term in place.

## NES sound hardware

### 2A03 (APU)

The NES's sound chip (Ricoh 2A03). Its audio portion, the APU (Audio Processing
Unit), generates all of the console's sound. SampleToNES emulates its four
melodic/percussive channels and no sampled-audio (DPCM) playback.

### Channel / oscillator

One of the 2A03's sound-producing units. There are four: two pulse, one
triangle, one noise. The two words are used interchangeably here.

### Pulse (square)

A channel that plays a square wave with a selectable duty cycle and 15 volume
levels. The chip has two of them (`pulse1`, `pulse2`).

### Triangle

A channel that plays a triangle wave of fixed shape and fixed volume; only its
pitch varies.

### Noise

A channel that plays pseudo-random noise from an LFSR, with 16 period settings,
15 volume levels, and a short/long mode.

### Duty cycle

The fraction of each period a pulse wave stays high (one of four settings). It
sets the pulse channel's timbre.

### LFSR

*Linear-feedback shift register* — the circuit that produces the noise channel's
pseudo-random pattern. Its short/long mode changes the pattern's length, and so
its character.

### NES frequency

How many times per second a program updates the channels — for example 60 Hz on
NTSC or 50 Hz on PAL. SampleToNES supports 15–600 Hz, and this rate sets the
reconstruction's frame rate.

### NTSC / PAL

The two console video standards. Their refresh rates (about 60 Hz and 50 Hz) are
the two most common NES frequencies.

## Reconstruction

### Reconstruction

The result of approximating an audio sample with the NES channels: one
instruction stream per channel plus the rendered audio. Saved as a `.stn` file.
See [Reconstruction algorithms](concepts/reconstruction.md).

### Instruction

A single command to one channel for one frame — on or off, *pitch*, *volume*, *duty
cycle* or *noise period*. It is the unit the reconstruction chooses per frame.

### Frame

A short, fixed-length slice of the input audio. Within a frame, each channel
holds one instruction. A frame's length is the sample rate divided by the NES
frequency.

### Instruction library

A precomputed catalogue holding, for every possible instruction, the waveform
its channel produces and that waveform's spectrum. The search draws its
candidates from the library. Saved as an `.ins` file. See
[Instruction libraries](formats/instruction-libraries.md).

### Approximation

The mixed, rendered audio a reconstruction produces — the NES channels' closest
match to the original sample.

### Working level (coefficient)

A single scale factor applied to the input so its typical loudness lands in the
amplitude range the NES channels can reproduce.

## Analysis and scoring

### Spectrum (feature, histogram)

A frame's frequency content — the representation matching compares, rather than
the raw waveform (two sounds that sound identical can have very different
waveforms).

### FFT / log-FFT / CQT

Three ways to compute a frame's spectrum, trading time resolution against
frequency resolution. CQT (the constant-Q transform) resolves low pitches finely
and is the default. See [Reconstruction algorithms](concepts/reconstruction.md).

### Gamma

A setting from 0 to 100 that reshapes the spectrum before comparison: 0 keeps
the raw power spectrum, 100 makes it logarithmic, and values in between
interpolate. Higher gamma emphasizes quiet detail relative to loud peaks.

### Criterion

The score that rates how well a candidate instruction matches a target frame. It
blends a spectral term (frequency shape) with a temporal term (waveform shape).

### β-divergence

The default per-bin spectral distance inside the criterion — a
Kullback–Leibler-style measure of how far one spectrum is from another.

### ERB / K-weighting

Perceptual weightings applied so each frequency bin counts in proportion to how
the ear hears it: ERB spaces bins by auditory critical bands, and K-weighting
applies a loudness curve.

### Selector

The strategy that searches the library for each frame's instructions. The
**greedy** selector treats every frame independently; the **Viterbi** selector
(the default) favours continuity, changing a channel only when the gain in match
quality outweighs the cost of the change.

### Calibration

A repeatable experiment that tunes the criterion's settings by reconstructing a
fixed test set and scoring the results. See [Calibration](concepts/calibration.md).

### Referee / corpus

Terms from calibration: a *referee* is an independent audio-distance judge that
scores a reconstruction against its original; the *corpus* is the fixed set of
synthetic test sounds every configuration is run against.

## Tracker and export

### FamiTracker

A [_tracker application_](http://famitracker.com/) for composing music for the
NES 2A03. SampleToNES exports instruments and modules that it (and its forks)
can load.

### Tracker / sequencer

A pattern-based music editor. SampleToNES's built-in sequencer arranges
reconstructed samples into a song.

### Sequence

In a FamiTracker instrument, a per-tick envelope for one dimension: volume,
arpeggio, pitch, hi-pitch, or duty/noise mode.

### Pattern

A block of tracker rows spanning the channels. A song plays its patterns in an
order.

### Order

The list that arranges patterns into the song's timeline.

### Module

A complete FamiTracker song, saved as an `.ftm` file — its settings,
instruments, patterns, and order together.

### Sample (sequencer)

A reconstruction added to the sequencer as a playable, placeable voice in the
song.

### Instrument

A single FamiTracker instrument, saved as an `.fti` file, exported from one
channel of a reconstruction. See [FamiTracker export](formats/famitracker.md).

## File types

| Extension | Contents |
| --- | --- |
| `.ins` | [Instruction library](formats/instruction-libraries.md) — the candidate catalogue. |
| `.stn` | [Reconstruction](formats/reconstructions.md) — a converted sample. |
| `.stp` | [Project](formats/projects.md) — a bundle of reconstructions with a song and settings. |
| `.fti` | FamiTracker instrument ([export](formats/famitracker.md)). |
| `.ftm` | FamiTracker module ([export](formats/famitracker.md)). |
