# Configuration file

The generation [configuration](../guide/configuration.md) is stored as a JSON
file, `config.json`, in the documents folder (see
[Where your files live](../guide/files.md)). The interface reads and writes it,
and you can edit it by hand to reach settings the interface does not expose. This
page documents its structure; [Reconstruction algorithms](../concepts/reconstruction.md)
explains what the settings do and lists the defaults.

The file has three sections — `general`, `library`, and `generation` — plus a
`metadata` block that records the application version and is managed
automatically. Unknown keys are rejected, so every key must be one of those below.

## `general`

Audio preprocessing and housekeeping.

| Key | Meaning | Values |
| --- | --- | --- |
| `normalize` | normalize the input before matching | `true` / `false` |
| `quantize` | quantize (bit-crush) the input | `true` / `false` |
| `quantization_levels` | number of levels when quantizing | integer ≥ 3 |
| `min_pitch`, `max_pitch` | lowest and highest pitch the reconstruction may use | 1–127 |
| `coefficient_percentile` | percentile of frame levels used to set the [working level](../concepts/reconstruction.md) | 0–100 |
| `coefficient_audibility_floor` | floor applied when estimating the working level | 0–1 |
| `max_workers` | worker processes used during reconstruction | integer ≥ 1 |
| `library_directory` | where instruction libraries are stored | path |
| `reconstructions_directory` | where reconstructions are written (alias: `output_directory`) | path |

## `library`

What defines the [instruction library](../concepts/instruction-library.md);
change any of these and a different library is selected or generated.

| Key | Meaning | Values |
| --- | --- | --- |
| `nes_frequency` | instruction change rate in Hz (alias: `change_rate`) | 15–600 |
| `sample_rate` | audio sample rate in Hz | 8000–192000 |
| `spectrum_method` | how the spectrum is computed | `fft` / `logfft` / `cqt` |
| `transformation_gamma` | feature-space scaling (0 keeps the power spectrum, 100 is logarithmic) | 0–100 |
| `a4_frequency`, `a4_pitch` | tuning reference: the frequency of A4 and its pitch number | — |

## `generation`

Which channels are used, and how candidates are scored. It carries a few
top-level keys and groups the scoring controls into `calculation`, `weights`,
`metric`, and `decoder`.

| Key | Meaning | Values |
| --- | --- | --- |
| `generators` | channels used | list of `pulse1`, `pulse2`, `triangle`, `noise` |
| `drive` | how hard the channels are pushed (alias: `mixer`) | > 0 |
| `reset_phase` | reset oscillator phase within each instruction | `true` / `false` |
| `final_regeneration` | re-render the chosen instructions at the end to keep oscillators continuous | `true` / `false` |

### `generation.calculation`

| Key | Meaning | Values |
| --- | --- | --- |
| `find_best_phase` | align each candidate to the target's phase before scoring | `true` / `false` |
| `fast_difference` | compare spectral features only, skipping a re-analysis of the residual | `true` / `false` |
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
| `temporal_level_floor` | floor for the temporal term's normalization | > 0 |

### `generation.decoder`

| Key | Meaning | Values |
| --- | --- | --- |
| `selector` | search strategy | `greedy` / `viterbi` |
| `top_k` | candidates kept per channel per frame | integer ≥ 1 |
| `pitch_weight`, `volume_weight`, `timbre_weight`, `on_off_weight` | Viterbi transition costs for changing each dimension | ≥ 0 |

## Editing the file

Keep to the keys above — unknown keys are rejected. The interface overwrites
`config.json` when you change a setting there, so the keys it does not expose (the
`metric`, `decoder`, phase aligner, and similar) are the ones you will typically
hand-edit. To keep several setups side by side, save them as separate files and
load one with `--config` (see [Command line](../guide/command-line.md)) or from the
**Reconstruction ▸ Load generation settings...** menu.
