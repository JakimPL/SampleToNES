# Calibration

The [reconstruction criterion](reconstruction.md) is full of tunable choices — the
spectrum method, gamma, the perceptual exponent on the loudness curve, the
spectral/temporal blend, the Viterbi transition weights — and their best values are
an empirical question. **Calibration** answers it with a repeatable experiment:
reconstruct a fixed probe corpus under several candidate configurations and let
independent judges score the results, so configuration decisions rest on measured
quality and targeted listening. The harness lives in `sampletones_core.calibration`
and runs as a script:

```
python scripts/calibration.py [--config <base>] [--methods fft,cqt]
    [--perceptual-exponents 0.5,1.0] [--temporal-weights 0.1,0.3]
    [--channels pulse1,triangle,noise]
```

The base configuration comes from `--config` when given; otherwise the saved
application configuration is used, so a run inherits the current app settings —
sample rate, gamma, selector and the rest. The channel set is the exception:
calibration pins the channels itself (`--channels`, by default pulse 1 +
triangle + noise), so every run reconstructs with an explicitly chosen channel
set and results stay comparable across machines.

It has three moving parts:

- **A synthetic corpus** (`calibration.corpus`) of short, deterministic probe
  signals in six categories: steady tones across the pitch range, pulse timbres
  of several duty cycles, white and dark noise, tone-plus-noise mixes,
  percussive transients (snare, kick, pluck) and a crescendo probing the dynamic
  range. Each probe is a `sampletones_synthesis` voice — oscillators, envelopes
  and filters composed from one shared, exactly-rendered configuration
  vocabulary — built from the probe families in
  `sampletones_config/calibration/corpus.yaml`. Each category isolates one kind of decision the criterion must get
  right — pitch, timbre, noise balance, attack sharpness, level tracking — and
  the fixed seed makes every run bit-identical, so scores are comparable across
  runs and code changes.
- **Variants** (`calibration.runner`): the requested knob values are swept as a
  cartesian product over a base configuration, each combination becoming a
  labeled, complete configuration. Missing instruction libraries are generated
  on the fly. Every corpus item is reconstructed under every variant, and the
  approximation is compared against the preprocessed original on the common
  scale set by the working level (see [Reconstruction](reconstruction.md)).
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
