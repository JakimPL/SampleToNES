# Calibration

Calibration measures how well _SampleToNES_ reconstructs a fixed set of reference sounds. It
converts each sound with each spectrum method, scores every result against the original, and
writes a page you listen to the results on.

Use it to:

- See which spectrum method suits which kind of sound.
- Check whether a new version or a changed setting reconstructs better or worse.
- Hear what a score means before trusting it.

## Run it

From a copy of the source code:

```
make calibration
```

In an installed copy:

```
sampletones calibration
```

The run takes a while, because it reconstructs every reference sound once for each variant. A first run
also builds the instruction libraries it needs.

With no options, the run measures the program's default settings under the packaged suite:

- Every spectrum method: `fft`, `logfft` and `cqt`.
- The channels pulse 1, triangle and noise for the synthetic sounds. The sounds written as NES frames
  are converted over all four channels.
- Every category of reference sound.
- Every other setting at its default value.

A *variant* is one configuration the run measured, named after its distinguishing settings. For
example, `cqt-pe1` is the `cqt` method at perceptual exponent 1. A *render* is one reference sound as a
variant reconstructed it.

The reference sounds are identical on every run, so figures from different versions compare.

The results go into a new folder inside the `calibration` folder of your
[SampleToNES folder](../guide/files.md). The folder is named by the date and time the run started, for
example `run-20260915-124501`. When the run ends, the command prints a link to the report and opens the
listening page.

## What a run writes

| Path | Contents |
|---|---|
| `index.html` | the listening page, which opens by double-click |
| `report.md` | the scores, as tables |
| `report.csv` | every score, one per row, for your own analysis |
| `renders/<variant>/` | a JSON file per reconstruction with its scores and the frames each channel plays, and a FLAC file of each listed one |
| `renders/<variant>/<sound>/` | each listed reconstruction cut by channel, one file per combination |
| `recordings/` | each reference sound, as the run prepared it for reconstruction: at the library's sample rate and the level the conversion matched |
| `corpus/` | the reference sounds as generated |
| `page/` | the stylesheet, the script and the palette the page reads |

The audio is FLAC, which is lossless and about a third of the size the same audio takes as WAV. A
default run writes about 35 MB. A run of four channels writes more, because a reconstruction of four
channels is cut into fourteen combinations and one of three channels into six.

## Listen on the page

Every run writes `index.html` and opens it when it ends. The page has one row per reference sound and
one column per variant. Each cell has:

- **play**, which sounds the whole reconstruction from its beginning.
- The score under it. The line below the score says how much of the distance between silence and the
  recording the reconstruction covers, or **past silence** where silence scores closer than the
  reconstruction does.
- One bar per channel, showing the frames that channel plays, in the channel's own color.

Beside each bar, **S** plays that channel alone and **M** plays every other channel. You hear what one
channel contributes and what the rest sound like without it. Both are separate recordings the run wrote,
so switching between them is exact.

<kbd>Space</kbd> pauses and resumes, <kbd>&larr;</kbd> and <kbd>&rarr;</kbd> move across one
sound's versions, and <kbd>&uarr;</kbd> and <kbd>&darr;</kbd> move to another sound.

The page is drawn in the program's own colors. `--palette NAME` draws it in another of the
program's palettes, and `--no-open` leaves it closed and prints its link alone.

A render plays at the same level as its recording, so a quieter render sounds quieter. You can also
play any file in the run folder in an audio player of your own.

Beside each render, a JSON file of the same name has:

- `judgments`: every referee's score for the render, with the readings behind it.
- `silence`: what complete silence would score against the same recording.
- `timelines`: one character per frame for each channel, `1` where that channel plays.

A render that scores worse than silence is a sign to listen before trusting the number.

## Read the report

A *referee* is a method that scores a reconstruction against its original: zero for identical signals,
higher for a larger audible difference. [How it judges](#how-it-judges) describes them.

`report.md` has one section per [family](#the-reference-sounds) of reference sounds, and in it one
subsection per referee. Each subsection starts with a table: one row per variant, one column per
category of the family, and the family's mean last. Lower is better. Each family is read on its own
terms, so a mean spans one family.

The `mr-loudness-dB` section adds a table for each of its readings:

- `missing`: content the original has and the reconstruction lacks. A high value sounds dull.
- `added`: content the reconstruction brings in. A high value sounds buzzy or noisy.
- `level`: how much louder the reconstruction plays than the original, in decibels. A negative value
  means quieter.

The score is `missing` plus `added`. `level` is reported separately.

The `transcription`, `pitch`, `stability`, `balance` and `continuity` sections read the reconstruction's
instructions against what a reference sound plays, so they cover only the sounds whose frames or
pitches the run knows. A synthesized sound of a known pitch carries it as a line, frame by frame: the
sines, the pulse waves, and the pitched `sines-` and `tones-` sounds. A decaying sound counts as
sounding its pitch while it stays within 40 dB of its start.
Their readings are shares of frames, from 0 to 1, except where the
[referees](#the-truth-referees) say otherwise. Lower is better there too.

## Custom runs

Each option replaces one part of the default run. The rest stays as the suite sets it.

| Option | What it changes | Example |
|---|---|---|
| `--config FILE` | Measures the settings in a configuration file instead of the defaults | the `config.json` in your [SampleToNES folder](../guide/files.md) holds your saved settings |
| `--methods LIST` | The spectrum methods measured | `--methods cqt` |
| `--channels LIST` | The channels every variant reconstructs the synthetic sounds with | `--channels pulse1,pulse2,triangle,noise` |
| `--categories LIST` | The categories of reference sounds measured | `--categories nes-pulse,nes-mix` |
| `--skip LIST` | The families or categories of reference sounds left out | `--skip composites` |
| `--workers N` | How many sounds are converted at once; without it, the `general.max_workers` of the configuration | `--workers 3` |
| `--resume` | Takes up the run in `-o` where it stopped | `-o before --resume` |
| `--corpus FILE` | Adds the sounds a manifest names to the packaged ones; see [your own sounds](#your-own-sounds) | `--corpus nesmdb.yaml` |
| `--perceptual-exponents LIST` | The perceptual exponents measured, one variant each | `--perceptual-exponents 0.5,1` |
| `--temporal-weights LIST` | The temporal loss weights measured, one variant each | `--temporal-weights 0.1,0.3` |
| `-o DIR`, `--output DIR` | The folder the run writes into | `-o before` |
| `--palette NAME` | The palette the listening page is drawn in | `--palette light` |
| `--no-open` | Leaves the page closed | `--no-open` |

A run writes `run.json` beside its report: what it measures, as fingerprints of its variants, its
channels and its sounds. With `--resume`, a run in the same folder measuring the same converts only the
sounds it has no record of yet, so a run stopped halfway goes on from there. A folder holding a run
measured otherwise is refused, with what differs.

Lists are comma separated. Several lists multiply: `--methods fft,cqt --perceptual-exponents
0.5,1` measures four variants, and the run takes about four times as long as one variant.

From a copy of the source code, put `uv run` in front: `uv run sampletones calibration --methods cqt`.

## Your own sounds

A manifest names reference sounds kept on your own machine, which join the packaged ones with
`--corpus FILE`. It is a YAML file with a list of `items`. Every path in it is read from the
manifest's own folder.

A manifest names two kinds of sound.

**Recordings** are audio files of your own, one recording or several stems under a stems setup in the
format `sampletones convert --stems` reads:

```yaml
items:
  - kind: recording
    name: song
    family: composites
    category: song
    listed: true
    sources: [stems/Vocals.wav, stems/Drums.wav, stems/Bass.wav, stems/Others.wav]
    stems: stems/setup.json
```

`family` is `composites` for stems and `samples` for a single recording kept to listen to. A
single recording leaves out `stems` and is converted over the run's channels.

**NES-MDB pieces** come from [NES-MDB](https://github.com/chrisdonahue/nesmdb), a collection of NES game music
transcribed from what the console's sound chip played. Download its MIDI archive yourself; the pieces
are read straight out of it.

```yaml
items:
  - kind: nesmdb
    name: castlevania-vampire-killer
    archive: nesmdb_midi.tar.gz
    member: nesmdb_midi/train/045_Castlevania_01_02VampireKiller.mid
    start_frame: 0
    frames: 448
    split: review
```

A piece plays `frames` frames from `start_frame`, at the run's NES frequency, and joins the
`sequences` family as a round trip: the run knows every frame it plays. `split` puts it in one of two
categories:

- `nesmdb-review`: pieces you listen to. The page lists them.
- `nesmdb-held-out`: pieces kept out of listening. The run measures them and writes their records,
  and no audio. A change that improves the review pieces counts once the held-out ones agree, since
  nothing was tuned on them.

## Compare runs

1. Run calibration into a folder of its own, for example `-o before`.
2. Change what you want to compare: install another version, or pass another `--config`.
3. Run calibration again into another folder, for example `-o after`.
4. Build one page over both:

```
sampletones calibration --board before after -o comparison
```

The page holds one tab per variant, with the runs side by side and the change between them in the
last column. It carries the audio it plays, so the `comparison` folder moves as one piece. Without
`-o` the page lands in a timestamped folder under `calibration/pages`.

`--board` reads finished runs and measures nothing, so it takes none of the options that measure.

To compare two versions of the source code, run each version from its own copy of the repository,
for example a `git worktree`, into its own folder.

## How it judges

### The reference sounds

The reference sounds are short clips, made the same way on every run. They come in families, which the
report and the page present in this order:

| Family | Sounds | Played exactly by the channels |
|---|---|---|
| `sines` | sine tones: steady, decaying, swinging in pitch, and a bass line | no |
| `notes` | single notes of every channel, laid on a grid | yes |
| `chords` | two to four channels held together | yes |
| `sequences` | melodies, bass lines, drums and pieces written as NES frames | yes |
| `tones` | sounds of other shapes: pulse waves, sawtooths, a vowel, plucks, noise, attacks, level changes | no |
| `composites` | several sounds together | no |

The page lists a selection of each family. The run measures every sound, writes the audio of the
listed ones, and keeps a record of the scores for the rest.

The synthetic sounds are generated from oscillators, envelopes and noise. Each category tests one kind
of decision:

| Category | Family | Sounds | What it tests |
|---|---|---|---|
| `tone` | `sines` | sines across the pitch range | pitch |
| `sines-decaying` | `sines` | sines at 110, 220, 440 and 880 Hz, struck once and left to decay at three speeds | holding one shape through a decay |
| `sines-vibrato` | `sines` | sines at 110 and 440 Hz swinging 25, 50 and 100 cents, 5.5 times a second | following a vibrato |
| `sines-line` | `sines` | a bass line from E1 to E3 of separated sine notes | a bass line, the lowest notes above all |
| `timbre` | `tones` | pulse waves of several duty cycles, 33% among them | the shape of a tone |
| `tones-line` | `tones` | the same bass line on a sawtooth | a bass line of a rich tone |
| `tones-voice` | `tones` | a melody on a vowel-like tone, its pitch swinging slightly | a sung line |
| `tones-pluck` | `tones` | plucked tones at 110 and 220 Hz | a decay whose timbre changes |
| `tones-vibrato` | `tones` | a sawtooth at 220 Hz swinging 25, 50 and 100 cents | a vibrato on a rich tone |
| `noise` | `tones` | white noise, and dark noise | noise without a pitch |
| `transient` | `tones` | a snare, a kick, a plucked tone | attacks and decays |
| `dynamics` | `tones` | a crescendo, and a loud burst dropping to a quiet hiss | following the level |
| `mix` | `composites` | a tone under hiss, and a bass under hi-hat ticks | a tone and noise together |
| `polyphony` | `composites` | a chord, and a melody over a snare | several voices at once |
| `mix-stems`, `polyphony-stems` | `composites` | the same composites, the tone and the noise each a stem | each part matched on the channels it may take |
| `composites-band` | `composites` | the sawtooth bass, the vowel melody and a drum pattern, each a stem: the bass on the triangle, the melody on either pulse, the drums on the noise | a small band converted as stems |

The `notes`, `chords` and `sequences` families are written out frame by frame, as instructions the
four channels play, and rendered the way the channels play them. Each one is a *round trip*: the
program could in principle play it back exactly, and the run knows every frame it should find. They use
plain notes and volumes, with no bends or sweeps.

The single notes are laid on a grid, each held for 36 frames and then silent for 12:

| Category | Notes |
|---|---|
| `notes-pulse` | every perfect fourth from note 33 to 118, at volumes 15, 7, 3 and 1, with the 12.5% and 50% duty cycles and one of 25% and 75% in turn |
| `notes-triangle` | every perfect fourth from note 33 to 118 |
| `notes-noise` | all 16 periods in both modes, at volumes 15, 7, 3 and 1 |

The page lists the loudest of them at every fourth pitch and every fifth period. `--skip notes` leaves
the family out, which shortens a run considerably.

| Category | Chords |
|---|---|
| `chords-two` | two pulses in a unison, third, fifth and octave; a pulse over a triangle bass; a tone and the noise |
| `chords-three` | a triad on two pulses and the triangle, loud and quiet; two pulses and hiss |
| `chords-four` | every channel at once |

| Category | Sequences |
|---|---|
| `sequences-melody` | a pulse melody from C3 to C6, plucked notes, a triangle melody, and a fast passage of 6-frame notes |
| `sequences-bass` | a triangle bass line from E1 to E3 |
| `sequences-drums` | a kick, snare and hat pattern from the noise channel's decays |
| `sequences-mixed` | a melody over a bass, two pulses in intervals, a chord progression, and a short piece on all four channels |

A round trip is converted over all four channels, so the run also hears whether the channels a sound
leaves out stay silent.

Every chord and sequence, NES-MDB pieces included, is converted a second time channel by channel: each
channel's frames become a stem of their own, held to that channel. Those conversions fall in the same
categories with `-by-channel` added, such as `chords-two-by-channel`. Set beside the first conversion,
they tell a failure to take the parts apart from a failure to match each part.

### The referees

Referees score in their own way, separate from the reconstruction's own scoring, so a comparison stays
fair when that scoring is what changed.

Both built-in referees split each signal into bands spaced the way hearing spaces pitch, at several
time resolutions, and compare the energy in each band in decibels.

- **`mr-auditory-dB`** averages the difference over every band equally. It reads the balance of
  tone against noise across the whole spectrum. An empty band counts as much as a full one, so a clip
  that adds noise to a lone tone scores worse than silence. The report lists this referee first.
- **`mr-loudness-dB`** weighs each band by how loud it plays, so the parts you hear carry the score
  and silent bands barely count. It first brings the reconstruction to the original's level and
  reports the level difference on its own. Silence scores worst, and a clip with the right tone and
  some added noise scores between.
- **`ownership`** reads a conversion of several stems on its own. It counts how often each channel
  passes from one stem to another per second. A pause between one stem's stretches counts for
  nothing. The score is the changes per second over every channel, and each channel's own reading
  follows. A conversion of one recording has no reading.
- **`contour`** follows the loudness of the recording over time and over the spectrum. Both are cut
  into frames of 1/60 s, each measured as its level in decibels. Over the frames the recording sounds
  in, the score is how far the render's levels stray from the recording's once a constant offset is
  set aside, in decibels. Its readings:
  - `spread`: the range of the render's levels less the recording's. Flattened dynamics read below
    zero.
  - `onset`: how much louder the render plays than the recording in the first three frames after a
    silence. An overshooting attack reads above zero.
  - `band-63` to `band-8000`: the render's energy less the recording's in each octave band the
    recording fills, in decibels. Read across, they draw any equalization the reconstruction adds.
- **`zimtohrli`** is a model of human hearing from Google. It joins the other two where it is
  installed. See [dependencies](../development/release/dependencies.md#calibration).

### The truth referees

A sound written as NES frames comes with every frame it plays, and its tonal channels give the pitch it
sounds in every frame. Three more referees read a reconstruction's instructions against that truth.
They never listen, so they say *what* went wrong where the audio referees say how much it shows.

- **`transcription`** counts the frames a channel plays as written. A frame counts wherever the
  sound or the reconstruction plays the channel, so a channel the sound leaves silent and the
  reconstruction sounds counts against it. A frame is played as written where both play it and every
  field agrees: the note, the duty cycle, the noise period and mode, and the volume within one step. The
  25% and 75% duty cycles count as one, since one wave is the other turned upside down and sounds the
  same.
  The two pulses sound the same mix whichever carries which line, so each frame pairs them the way
  that agrees more. The score is the share of counted frames played otherwise. Its readings:
  - `missed`: written frames the reconstruction leaves silent.
  - `spurious`: played frames the sound leaves silent.
  - `note`, `duty`, `volume`, `period`, `mode`: frames both play where that field disagrees.
- **`pitch`** answers every frame a line of the sound plays with the closest note a tonal channel of
  the reconstruction sounds then, whichever channel that is. The score is the share of frames not
  answered within half a semitone. Its readings are the share answered an `octave` off (the right
  note in another octave), a `semitone` off, by a `wrong` note, or left `silent`, and `cents`: how far
  the answers on pitch stand from the line, on average, in cents.
- **`stability`** counts how often channels change: turning on or off (`toggles`), or moving to another
  note or noise period while sounding (`moves`). The score is how many more changes per second the
  reconstruction makes than the sound itself, the two readings together. A reconstruction that
  flickers where the sound holds still scores high. Three more readings measure how far the sounding
  channels move per second, beyond the sound's own motion:
  - `pitch-motion`: semitones the sounding pitch travels, bends included, so a vibrato the
    reconstruction follows counts as the sound's own.
  - `level-motion`: decibels the volume of a sounding pulse or noise channel travels.
  - `duty-switches`: changes of a sounding pulse's timbre, 25% and 75% being one.

  The last two need the sound's own frames.
- **`balance`** compares how the channels share the sound out. A part's share is its energy over
  the energy of every part, the two pulses one part. The score is the share that would have to move
  between parts to match the sound, from 0 to 1. Its readings:
  - `pulses`, `triangle`, `noise`: each part's share played less its share written. A triangle
    whose line went to a pulse reads below zero.
  - `bass-on-pulse`: the share of the triangle's frames whose note a pulse plays, in any octave,
    while the triangle plays another or none.
  - `scale`: how much the reconstruction scaled the sound before matching it. A round trip matched
    at the level the channels play it reads 1.
- **`continuity`** asks whether each note of the sound comes back as one continuous sound. A note
  is a run of frames a line holds one pitch through. In each of its frames the note is answered by
  the tonal channel sounding closest to it, or by none. The score is the extra events per note:
  - `handovers`: changes of the answering channel, such as a triangle note a pulse takes over
    halfway.
  - `fragments`: separate sounding runs per note. A note heard whole has one; a dropout in the
    middle makes two.
