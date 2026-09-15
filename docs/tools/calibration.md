# Calibration

Calibration measures how well _SampleToNES_ reconstructs a fixed set of reference sounds. It
converts each sound with each spectrum method, scores every result against the original, and
writes every result as a WAV file you can listen to.

Use it to:

- see which spectrum method suits which kind of sound;
- check whether a new version or a changed setting reconstructs better or worse;
- hear what a score means before trusting it.

## Run it

From a copy of the source code:

```
make calibration
```

In an installed copy:

```
sampletones calibration
```

The run takes several minutes. A first run also builds any instruction library it is missing,
which adds to the time.

With no options, the run measures the program's default settings under the packaged suite:

- every spectrum method: `fft`, `logfft` and `cqt`;
- the channels pulse 1, triangle and noise;
- every other setting at its default value.

The same run on another machine or another version gives figures that compare directly, because
the reference sounds are generated from a fixed seed.

The results go into a new folder under `Documents/SampleToNES/calibration/`, named by the date and
time the run started, for example `run-20260915-124501`. When the run ends, it prints a link to
the report.

## What a run writes

| Path | Contents |
|---|---|
| `report.md` | the scores, as tables |
| `report.csv` | every score, one per row, for your own analysis |
| `renders/<variant>/` | each reconstruction as a WAV file, and a JSON file with its scores and the frames each channel plays |
| `recordings/` | each reference sound, as the run prepared it for reconstruction |
| `corpus/` | the reference sounds as generated |

A *variant* is one configuration the run measured, named after the settings that set it apart,
for example `cqt-pe1` for the `cqt` method at perceptual exponent 1. A *render* is one reference
sound as a variant reconstructed it.

## Listen to the renders

Open the run folder and play the files in any audio player:

- `recordings/tone-220hz.wav` is the reference sound;
- `renders/cqt-pe1/tone-220hz.wav` is the same sound as the `cqt-pe1` variant reconstructed it.

A render plays at the same gain as its recording, so a render that sounds quieter is quieter.

Beside each render, a JSON file of the same name holds:

- `judgments`: every referee's score for the render, with the readings behind it;
- `silence`: what complete silence would score against the same recording;
- `timelines`: one character per frame for each channel, `1` where that channel plays.

A render that scores worse than silence is a sign to listen before trusting the number.

## Read the report

`report.md` holds one section per referee. Each section starts with a table: one row per variant,
one column per category of reference sound, and the overall mean last. Lower is better.

The `mr-loudness-dB` section adds a table for each of its readings:

- `missing`: content the original has and the reconstruction lacks. A high value sounds dull.
- `added`: content the reconstruction brings in. A high value sounds buzzy or noisy.
- `level`: how much louder the reconstruction plays than the original, in decibels. Negative means
  quieter.

`missing` and `added` add up to the score. The level is reported apart from the score.

## Custom runs

Each option replaces one part of the default run. The rest stays as the suite sets it.

| Option | What it changes | Example |
|---|---|---|
| `--config FILE` | Measures the settings in a configuration file instead of the defaults | `--config ~/Documents/SampleToNES/config.json` measures your saved settings |
| `--methods LIST` | The spectrum methods measured | `--methods cqt` |
| `--channels LIST` | The channels every variant reconstructs with | `--channels pulse1,pulse2,triangle,noise` |
| `--perceptual-exponents LIST` | The perceptual exponents measured, one variant each | `--perceptual-exponents 0.5,1` |
| `--temporal-weights LIST` | The temporal loss weights measured, one variant each | `--temporal-weights 0.1,0.3` |
| `-o DIR`, `--output DIR` | The folder the run writes into | `-o ~/calibration/before` |

Lists are comma separated. Several lists multiply: `--methods fft,cqt --perceptual-exponents
0.5,1` measures four variants, and the run takes about four times as long as one variant.

From a copy of the source code, put `uv run` in front: `uv run sampletones calibration --methods cqt`.

The default suite is the file `sampletones_tools/calibration/config/suite.yaml` in the package.

## Compare runs

1. Run calibration into a folder of its own, for example `-o ~/calibration/before`.
2. Change what you want to compare: install another version, or pass another `--config`.
3. Run calibration again into another folder, for example `-o ~/calibration/after`.
4. Compare the two `report.md` files, and play the same render from both folders.

Both runs generate the same reference sounds, so every score and every render compares directly.

To compare two versions of the source code, run each version from its own copy of the repository,
for example a `git worktree`, into its own folder.

## How it judges

### The reference sounds

The reference sounds are short synthetic clips, generated the same way on every run. Each category
tests one kind of decision:

| Category | Sounds | What it tests |
|---|---|---|
| `tone` | sines across the pitch range | pitch |
| `timbre` | pulse waves of several duty cycles | the shape of a tone |
| `noise` | white noise, and dark noise | noise without a pitch |
| `mix` | a tone under hiss, and a bass under hi-hat ticks | a tone and noise together |
| `transient` | a snare, a kick, a plucked tone | attacks and decays |
| `dynamics` | a crescendo, and a loud burst dropping to a quiet hiss | following the level |
| `polyphony` | a chord, and a melody over a snare | several voices at once |

The sounds and their parameters are defined in `sampletones_tools/calibration/config/corpus.yaml`.

### The referees

A referee compares a reconstruction with its original and returns a score: zero for identical
signals, higher for a larger audible difference. Referees measure in their own way, apart from the
reconstruction's own scoring, so a comparison stays fair when that scoring is what changed.

Both built-in referees split each signal into bands spaced the way hearing spaces pitch, at several
time resolutions, and compare the energy in each band in decibels. Their tuning is in
`sampletones_tools/calibration/config/referee.yaml`.

- **`mr-auditory-dB`** averages the difference over every band equally. It reads the balance of
  tone against noise across the whole spectrum. Because an empty band counts as much as a full one,
  a clip that adds noise to a lone tone scores worse than silence. The report still lists this
  referee first.
- **`mr-loudness-dB`** weighs each band by how loud it plays, so the parts you hear carry the score
  and silent bands barely count. It first brings the reconstruction to the original's level and
  reports the level difference on its own. Silence scores worst, and a clip with the right tone and
  some added noise scores between.
- **`zimtohrli`** is a model of human hearing from Google. It joins the other two where it is
  installed; see [dependencies](../development/release/dependencies.md#calibration).

A referee is tested against sounds whose ranking is known, such as "a triangle at the right pitch
is closer to a sine than silence is". These tests live in
`tests/unit/sampletones_tools/calibration/referee/test_axioms.py`. A test a referee is known to
fail is marked as an expected failure.

### Which referee leads

The report lists `mr-auditory-dB` first until `mr-loudness-dB` is shown to agree with the ear: rated
by ear, a sweep of renders must rank the way its scores do, with a rank correlation of at least 0.6
in every category.
