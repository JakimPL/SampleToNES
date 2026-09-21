# Glossary

Short definitions of the terms used across the documentation, grouped by area. Other pages link here
instead of explaining a term again.

## NES sound hardware

### 2A03 (APU)

The NES's sound chip (Ricoh 2A03). Its audio part, the APU (Audio Processing Unit), makes all of the
console's sound. _SampleToNES_ emulates its four melodic and percussive channels. DPCM sample playback is
outside its scope.

### Channel

One of the 2A03's four sound units: `pulse1`, `pulse2`, `triangle` and `noise`. A *generator* is a
different thing: the kind of oscillator an instruction library covers (`pulse`, `triangle`, `noise`),
and the classes that implement it.

### Pulse (square)

A channel that plays a square wave. Its duty cycle is selectable and it has 15 volume levels. The chip
has two independent pulse channels: `pulse1` and `pulse2`.

### Triangle

A channel that plays a triangle wave of fixed shape and volume. Only its pitch varies. Its timer divides
the APU clock by 32 where the pulse timers divide by 16, and all three read the same period table. A
triangle note therefore sounds an octave below the pulse note with the same period, so a triangle
instruction of pitch P sounds at pitch P−12. FamiTracker uses the same convention, so an exported note
plays at the pitch _SampleToNES_ played it.

### Noise

A channel that plays pseudo-random noise from an [LFSR](#lfsr). It has 16 period settings, 15 volume
levels and a short and a long mode.

### Duty cycle

The fraction of each period a pulse wave stays high, in one of four settings. It sets the pulse channel's
timbre.

### Divider

The number a tone channel counts down from. It sets the pitch, and a smaller divider gives a higher note.

### LFSR

*Linear-feedback shift register*: the circuit that makes the noise channel's pseudo-random pattern. Its
mode sets the pattern's length and so its character. Long mode repeats every 32767 shifts and sounds like
noise. Short mode repeats every 93 shifts, so a high period setting sounds as a tone of metallic timbre.

### NES frequency

How many times per second a program updates the channels, for example 60 Hz on NTSC or 50 Hz on PAL.
_SampleToNES_ accepts 15–300 Hz, and the rate sets the reconstruction's frame rate.

### NTSC / PAL

The two console video standards. Their refresh rates, about 60 Hz and 50 Hz, are the most common NES
frequencies.

## Reconstruction

### Reconstruction

The result of approximating an audio sample with the NES channels: one instruction stream per channel
plus the rendered audio. Saved as a `.stn` file. See
[Reconstruction algorithms](concepts/reconstruction.md).

### Instruction

A command to one channel for one frame: on or off, *pitch*, *volume*, *duty cycle* or *noise period*.
The reconstruction picks one per channel for each frame.

### Frame

A short slice of the input audio. All frames have the same length: the sample rate divided by the NES
frequency. Each channel plays one instruction in a frame. The sequencer also uses the word for one
position in the [order](#order): the patterns the song plays at that point.

### Tick

One update of the channels, at the NES frequency. A tick lasts as long as a frame. Envelopes advance one
item per tick, and a tracker row lasts one or more ticks.

### Stem

One recording that goes into a reconstruction. Every conversion is a stems conversion. A single file is
one stem that takes every channel it is given, and several recordings share the channels between them. A
reconstruction records which channels each stem was given and which frames it played, so you can hear,
edit or remove one stem on its own. See [Stems reconstruction](concepts/stems.md) and
[Converting audio](guide/converting.md).

### Level (stems)

The rank a stem takes when the channels are shared out. A stem on level 1 is offered channels before one
on level 2, so a lead part can take the channels it needs before a background part does.

### Drive

How hard a stem pushes a channel. It is set per channel when a conversion is set up. `1.00` is the level
the recording was measured at. A higher drive reaches for a louder match, which suits a part that sits
quietly under the others.

### Instruction library

A precomputed catalog of every possible instruction, with the waveform its channel produces and that
waveform's spectrum. The search draws its candidates from the library. Saved as an `.ins` file. See
[Instruction libraries](formats/instruction-libraries.md).

### Approximation

The mixed, rendered audio a reconstruction produces: the NES channels' closest match to the original
sample.

### Working level (coefficient)

A single scale factor applied to the input, so its typical frame plays at the level one NES channel
renders at full volume.

## Analysis and scoring

### Spectrum (feature, histogram)

A frame's frequency content. Matching compares spectra instead of raw waveforms, because two sounds that
sound alike can have very different waveforms.

### FFT / log-FFT / CQT

Three ways to compute a frame's spectrum. They trade time resolution against frequency resolution. CQT
(the constant-Q transform) resolves low pitches finely and is the default. See
[Reconstruction algorithms](concepts/reconstruction.md).

### Gamma

A setting from 0 to 100 that reshapes the spectrum before comparison. 0 keeps the raw power spectrum, 100
makes it logarithmic, and values between blend the two. Higher gamma emphasizes quiet detail over loud
peaks.

### Criterion

The score that rates how well a candidate instruction matches a target frame. It blends a spectral term
(frequency shape) with a temporal term (waveform shape).

### β-divergence

The default per-bin spectral distance in the criterion. It is a Kullback–Leibler-style measure of how far
one spectrum is from another.

### ERB / K-weighting

Perceptual weightings that make each frequency bin count as much as the ear hears it. ERB spaces bins by
auditory critical bands. K-weighting applies a loudness curve.

### Column

The candidates one channel may sound in a frame, best first. The decoder reads the columns into one
candidate per frame.

### Mix

The combined sound of the picks a stem already holds in a frame. A new candidate is scored as it would
sound beside the mix.

### Pick

The choice of one candidate for one channel in a frame. A frame is assigned pick by pick for as long as a
pick lowers the frame's cost.

### Resting

The state of a channel that no stem holds in a frame. It plays its null instruction, which keeps every
channel's stream in step with the frames.

### Standing by

The state of a channel whose stream has no frame. No export writes it and it costs nothing, and it stays
open to edit. See [Reconstructions](formats/reconstructions.md#instructions_data).

### Decoder

The strategy that reads a channel's per-frame candidates into the stream it plays. The setting is
`generation.decoder.selector`. The **greedy** decoder plays each frame's best candidate. The **Viterbi**
decoder, the default, favors continuity: it changes a channel only when the gain in match quality
outweighs the cost of the change.

### Calibration

A repeatable experiment that tunes the criterion's settings by reconstructing a fixed test set and
scoring the results. See [Calibration](tools/calibration.md).

### Referee / corpus / render / variant

Terms from calibration. A *referee* is an independent audio-distance judge that scores a reconstruction
against its original. The *corpus* is the fixed set of synthetic test sounds every configuration is run
against. A *render* is one reconstruction of a corpus sound, written as an audio file for listening. A
*variant* is one configuration a run measured.

## Tracker and export

### FamiTracker

A [_tracker application_](http://famitracker.com/) for composing music for the NES 2A03. _SampleToNES_
exports instruments and modules that it and its forks can load.

### Bitphase

A [_web tracker_](https://bitphase.app/) whose chips include the NES 2A03. _SampleToNES_
exports documents and instrument presets it can load. See [Bitphase export](formats/bitphase.md).

### Tracker / sequencer

A pattern-based music editor. _SampleToNES_'s built-in sequencer arranges reconstructed samples into a
song.

### Sequence (envelope)

A per-tick list of values that one dimension of a sound follows while a note is held. The dimensions are
volume, arpeggio, pitch, hi-pitch, and duty or noise mode. An **arpeggio** sequence steps the note itself
up and down. The **pitch** and **hi-pitch** sequences bend it in fine and coarse steps (see
[Bend](#bend)). A FamiTracker instrument has one sequence per dimension, and _SampleToNES_ edits the same
shapes.

### Bend

How far a frame sounds from the note it names, counted in steps of the channel's [divider](#divider).
The **pitch** sequence counts one step per item and the **hi-pitch** sequence sixteen, and the two add
up. A step is well under a cent at the lowest notes and widens to a whole semitone at the highest, where
the divider grid is already coarser than the note grid. Only the pulse and triangle channels read a bend.
The noise channel's 16 periods have no finer grid.

### Row

One line of a pattern. It says what each channel starts at that moment, and lasts one or more ticks.

### Pattern

A block of tracker rows spanning the channels. A song plays its patterns in an order.

### Metric highlight

The row grouping a song is counted in. The **first highlight** is the beat: the number of rows one beat
spans. The **second highlight** is the bar, which gathers beats. The tracker tints the row that opens
each. A tempo counts beats:
`beats_per_minute = 60 × nes_frequency / (ticks_per_row × first_highlight)`.

### Groove

The number of ticks each row of a pattern lasts. A row lasts a whole number of ticks, so a tempo between
two counts is played by varying the count from row to row. The meter places the longer rows on the bar
first, then on the beat, then inside the beat. Playback reads the groove by the row's position in the
pattern, so the pattern's first row starts it afresh.

### Order

The list that arranges patterns into the song's timeline.

### Module

A complete FamiTracker song, saved as an `.ftm` file: its settings, instruments, patterns and order
together.

### Document

A complete Bitphase project, saved as a `.btp` file: its songs, instruments, tables, patterns and order
together.

### Table

In Bitphase, a per-tick list of semitone offsets that a pattern cell attaches to a channel. It carries
the pitch contour a FamiTracker arpeggio sequence would.

### Voice

Anything a tracker row can name: a **sample** or an **instrument**. A project keeps its voices in one
list. A row says which voice to start and the step it plays at.

### Sample (sequencer)

A reconstruction added to the sequencer as a playable voice. It carries the instruction stream its
conversion found for each channel.

### Sample column

The tracker's leftmost data column. It places a sample across every channel the sample's reconstruction
covers, and clears the rest of the row. It takes samples only, because an instrument sounds on the one
channel that names it. Its cell summarizes what those channels hold and reads `?` where they disagree.
See [The sequencer](guide/sequencer.md#writing-a-pattern).

### Instrument

One set of envelopes a channel reads while a note sounds, saved as an `.fti` file. A hand-written voice is
a single instrument that goes on whichever channel suits it, as in FamiTracker. A sample has one
instrument per channel it plays. Bitphase takes the same envelopes as a `.json` instrument preset. See
[The sequencer](guide/sequencer.md), [FamiTracker export](formats/famitracker.md) and
[Bitphase export](formats/bitphase.md).

### Initial pitch

The value an instrument's frames are built at, and the note an exported preset is tuned to. A
hand-written instrument has one for the tonal channels and a period for the noise channel, so the same
envelopes sound on any of the four channels. The row that places the instrument sets the note it sounds
at. A sample's matching value is its per-channel [reference pitch](formats/reconstructions.md#contents).

### Loop point

The item a single envelope repeats from while a note is held. It lets an attack be followed by a
sustained tail. Each envelope has its own loop point, so a two-item duty cycle can circle on its own
period beside a longer volume envelope. An envelope without one holds its last item while the note
sounds.

## File types

| Extension | Contents |
| --- | --- |
| `.ins` | [Instruction library](formats/instruction-libraries.md) — the candidate catalog. |
| `.stn` | [Reconstruction](formats/reconstructions.md) — a converted sample. |
| `.stp` | [Project](formats/projects.md) — a bundle of reconstructions with a song and settings. |
| `.fti` | FamiTracker instrument ([export](formats/famitracker.md)). |
| `.ftm` | FamiTracker module ([export](formats/famitracker.md)). |
| `.btp` | Bitphase document ([export](formats/bitphase.md)). |
| `.nsf` | [NSF program](formats/nsf.md) — a song and the driver that plays it. |
| `.json` | Bitphase instrument preset ([export](formats/bitphase.md)), or the [configuration file](formats/configuration.md). |
