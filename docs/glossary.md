# Glossary

Recurring terms used across the documentation, grouped by area. Other documents
link here rather than redefining a term in place.

## NES sound hardware

### 2A03 (APU)

The NES's sound chip (Ricoh 2A03). Its audio portion, the APU (Audio Processing
Unit), generates all of the console's sound. _SampleToNES_ emulates its four
melodic/percussive channels and no sampled-audio (DPCM) playback.

### Channel

One of the 2A03's four sound-producing units: `pulse1`, `pulse2`,
`triangle`, and `noise`. The word *generator* names a distinct concept:
the oscillator kinds an instruction library covers (`pulse`, `triangle`,
`noise`) and the classes that implement them.

### Pulse (square)

A channel that plays a square wave with a selectable duty cycle and 15 volume
levels. The chip has two of them (`pulse1`, `pulse2`).

### Triangle

A channel that plays a triangle wave of fixed shape and fixed volume; only its
pitch varies. Its timer divides the APU clock by 32 while the pulse channels divide
by 16, and all three read the same period table, so a triangle note sounds an octave
below the note it is written as: a triangle instruction of pitch P sounds at pitch
P−12. FamiTracker uses the same convention, so an exported note cell plays at the
pitch _SampleToNES_ played it.

### Noise

A channel that plays pseudo-random noise from an LFSR, with 16 period settings,
15 volume levels, and a short/long mode. The period setting divides the APU clock
into the LFSR's shift rate, `APU_CLOCK / NOISE_PERIODS[index]`, spanning 440.0 Hz at
index 0 to 447443.2 Hz at index 15.

### Duty cycle

The fraction of each period a pulse wave stays high (one of four settings). It
sets the pulse channel's timbre.

### LFSR

*Linear-feedback shift register* — the circuit that produces the noise channel's
pseudo-random pattern. Its short/long mode changes the pattern's length, and so its
character: long mode repeats every 32767 shifts and reads as noise, short mode
repeats every 93 and turns a high period setting into an audible tone — index 15
sounds at 447443.2 ÷ 93 ≈ 4811 Hz. Short mode also carries a strong DC asymmetry, its
output bit set 17.2% of the time against long mode's 50%, and that bias is what gives
it its metallic timbre.

### NES frequency

How many times per second a program updates the channels — for example 60 Hz on
NTSC or 50 Hz on PAL. _SampleToNES_ supports 15–300 Hz, and this rate sets the
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

### Decoder

The strategy that reads a channel's per-frame candidates into the stream it plays,
named by `generation.decoder.selector`. The **greedy** decoder plays each frame's
best candidate; the **Viterbi** decoder (the default) favours continuity, changing a
channel only when the gain in match quality outweighs the cost of the change.

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
NES 2A03. _SampleToNES_ exports instruments and modules that it (and its forks)
can load.

### Bitphase

A [_web tracker_](https://github.com/paator/bitphase) whose chips include the NES
2A03. _SampleToNES_ exports documents and instrument presets it can load. See
[Bitphase export](formats/bitphase.md).

### Tracker / sequencer

A pattern-based music editor. _SampleToNES_'s built-in sequencer arranges
reconstructed samples into a song.

### Sequence

In a FamiTracker instrument, a per-tick envelope for one dimension: volume,
arpeggio, pitch, hi-pitch, or duty/noise mode.

### Pattern

A block of tracker rows spanning the channels. A song plays its patterns in an
order.

### Metric highlight

The row grouping a song is counted in. The **first highlight** is the beat — the
rows one beat spans — and the **second highlight** is the bar that gathers beats.
The tracker tints the row that opens each, and the beat is what a tempo counts:
`beats_per_minute = 60 × nes_frequency / (ticks_per_row × first_highlight)`.

### Groove

The engine ticks each row of a pattern lasts. An engine holds a row for a whole
number of ticks, so a tempo landing between two counts is played by varying the
count from row to row, and the metre places the longer rows on the bar, then the
beat, then inside the beat. Playback reads the groove by the row's position in the
pattern, so the pattern's first row starts it afresh.

### Order

The list that arranges patterns into the song's timeline.

### Module

A complete FamiTracker song, saved as an `.ftm` file — its settings,
instruments, patterns, and order together.

### Document

A complete Bitphase project, saved as a `.btp` file — its songs, instruments,
tables, patterns, and order together.

### Table

In Bitphase, a per-tick list of semitone offsets a pattern cell attaches to a
channel, which carries the pitch contour a FamiTracker arpeggio sequence would.

### Sample (sequencer)

A reconstruction added to the sequencer as a playable, placeable voice in the
song.

### Instrument

A single FamiTracker instrument, saved as an `.fti` file, exported from one
channel of a reconstruction. See [FamiTracker export](formats/famitracker.md).
Bitphase takes the same slice as a `.json` instrument preset. See
[Bitphase export](formats/bitphase.md).

## File types

| Extension | Contents |
| --- | --- |
| `.ins` | [Instruction library](formats/instruction-libraries.md) — the candidate catalogue. |
| `.stn` | [Reconstruction](formats/reconstructions.md) — a converted sample. |
| `.stp` | [Project](formats/projects.md) — a bundle of reconstructions with a song and settings. |
| `.fti` | FamiTracker instrument ([export](formats/famitracker.md)). |
| `.ftm` | FamiTracker module ([export](formats/famitracker.md)). |
| `.btp` | Bitphase document ([export](formats/bitphase.md)). |
| `.json` | Bitphase instrument preset ([export](formats/bitphase.md)), or the [configuration file](formats/configuration.md). |
