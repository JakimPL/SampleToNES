# Configuration file

The generation [configuration](../guide/configuration.md) is stored as a JSON file, `config.json`, in the
documents folder (see [Where your files live](../guide/files.md)). The interface reads and writes it, and
you can edit it by hand to reach settings the interface does not expose. This page documents its
structure. [Reconstruction algorithms](../concepts/reconstruction.md) explains what the settings do.

The file has three sections, `general`, `library` and `generation`, plus a `metadata` block. The block
records the application version and is managed automatically. Unknown keys are rejected, so every key
must be one of those below.

A key you leave out keeps its shipped value. The shipped values of the `generation` section are in
`sampletones_core/configs/generation.yaml`, which sets them for every copy of the program.

## `general`

Audio preprocessing and housekeeping.

| Key | Meaning | Values |
| --- | --- | --- |
| `normalize` | normalize the input before matching | `true` / `false` |
| `quantize` | quantize the input to fewer volume steps | `true` / `false` |
| `quantization_levels` | number of levels when quantizing | integer ≥ 3 |
| `min_pitch`, `max_pitch` | lowest and highest pitch the reconstruction may use | 1–127 |
| `coefficient_percentile` | percentile of the frames' RMS levels used to set the [working level](../concepts/reconstruction.md) | 0–100 |
| `coefficient_audibility_floor` | fraction of the loudest frame's level below which a frame is left out of the working level | 0 < value ≤ 1 |
| `max_workers` | worker processes used during reconstruction | integer ≥ 1 |
| `library_directory` | where instruction libraries are stored | path |
| `reconstructions_directory` | where reconstructions are written (alias: `output_directory`) | path |

## `library`

What defines the [instruction library](../concepts/instruction-library.md);
change any of these and a different library is selected or generated.

| Key | Meaning | Values |
| --- | --- | --- |
| `nes_frequency` | instruction change rate in Hz (alias: `change_rate`) | 15–300 |
| `sample_rate` | audio sample rate in Hz | 8000–192000 |
| `spectrum_method` | how the spectrum is computed | `fft` / `logfft` / `cqt` |
| `transformation_gamma` | feature-space scaling (0 keeps the power spectrum, 100 is logarithmic) | 0–100 |
| `a4_frequency` | tuning reference: what A4 sounds at, in Hz | 311 < value < 623 |
| `a4_pitch` | tuning reference: the pitch number A4 names | 24–127 |

## `generation`

How candidates are scored. It has one top-level key and groups the scoring controls into `calculation`,
`weights`, `metric`, `decoder` and `refinement`.

The channels a conversion uses, how hard each is pushed and how many a recording may sound at once are
set per recording in the converter. The [stems setup](reconstructions.md) a reconstruction carries
records them.

| Key | Meaning | Values |
| --- | --- | --- |
| `reset_phase` | reset oscillator phase within each instruction | `true` / `false` |

### `generation.calculation`

| Key | Meaning | Values |
| --- | --- | --- |
| `find_best_phase` | align each candidate whose frames repeat one waveform shape to the target's phase before scoring | `true` / `false` |
| `phase_aligner` | how the best phase is found | `sliding_rmse` / `cross_correlation` |

### `generation.weights`

| Key | Meaning | Values |
| --- | --- | --- |
| `spectral_loss_weight` | weight of the spectral term in the [criterion](../concepts/reconstruction.md) | ≥ 0 |
| `temporal_loss_weight` | weight of the temporal term | ≥ 0 |

### `generation.metric`

| Key | Meaning | Values |
| --- | --- | --- |
| `spectral_distance` | per-bin spectral distance | `squared` / `absolute` / `beta_divergence` |
| `beta` | β for the β-divergence | ≥ 0 |
| `perceptual_exponent` | exponent on the loudness weighting | ≥ 0 |
| `temporal_level_floor` | floor for the temporal term's normalization, as a share of what one channel plays at full volume | > 0 |
| `silence_floor` | the power a frame is measured from when its own bins all lie under it, so a silent frame's score stays finite | > 0 |
| `dynamic_range_decibels` | how far under a frame's loudest bin the comparison reaches | > 0 |

### `generation.decoder`

| Key | Meaning | Values |
| --- | --- | --- |
| `selector` | search strategy | `greedy` / `viterbi` |
| `top_k` | candidates kept per channel per frame | integer ≥ 1 |
| `pitch_weight`, `volume_weight`, `timbre_weight`, `on_off_weight` | Viterbi transition costs for changing each dimension | ≥ 0 |

### `generation.refinement`

| Key | Meaning | Values |
| --- | --- | --- |
| `confidence` | share of a frame's energy its harmonics must hold for its pitch reading to count | 0–1 |
| `change_weight` | divider steps of reading error worth avoiding one change of bend | ≥ 0 |
| `window` | frames on either side whose readings a frame may settle on | integer ≥ 0 |

## Editing the file

Use only the keys above, because unknown keys are rejected. The interface overwrites `config.json` when
you change a setting there. The keys it does not expose, such as `metric`, `decoder` and the phase
aligner, are the ones you typically edit by hand. To keep several setups side by side, save them as
separate files. Load one with `--config` (see [Command line](../guide/command-line.md)) or from the
**Reconstruction ▸ Load generation settings...** menu.
