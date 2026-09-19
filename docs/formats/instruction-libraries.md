# Instruction libraries

An instruction library is stored as a single `.ins` file holding, for every
possible instruction, the waveform its channel produces and that waveform's
[spectrum](../glossary.md#spectrum-feature-histogram). It is the catalog the
reconstruction search draws its candidates from. For what a library is and how
it is built, see [Instruction library](../concepts/instruction-library.md); this
page documents the file.

Libraries are generated from the _Instructions_ tab (or with
`sampletones library`) and stored in the documents folder.

## Contents

A library is keyed by the configuration that produces it and holds one entry per
instruction.

### Per-instruction data

Each entry contains:

* **metadata** — the generator class (`PulseGenerator` / `TriangleGenerator` /
  `NoiseGenerator`) and the instruction values below;
* **instruction values** — the channel command:
    * **on** (0–1) — whether the channel sounds;
    * **pitch** (33–119) for pulse and triangle, or **period** (0–15) for noise;
    * **volume** (0–15) for pulse and noise;
    * **duty_cycle** (0–3) for pulse, or the **short** (0–1) flag for noise;
* **waveform** — one full period of the rendered wave (the longest noise samples
  are trimmed to one second);
* **spectrum** — the waveform's precomputed frequency content.

### Configuration key

Each library corresponds to one configuration. The parameters that change the
rendered waveforms or their spectra — sample rate, NES frequency, FFT window
size, transformation gamma, and spectrum method — form its key, so changing any
of them selects (or generates) a different library. What gamma and the spectrum
method mean is covered in [Reconstruction algorithms](../concepts/reconstruction.md)
(§3.2–3.3).

## File format

Libraries are stored as `.ins` files in the documents folder, with the
configuration embedded in the file name:

```
sr_44100_nf_60_ws_13579_tg_0_sm_cqt_ch_384e710987cb958adf2b214df1267d10.ins
```

| Fragment | Meaning |
| --- | --- |
| `sr_44100` | sample rate 44100 Hz |
| `nf_60` | NES frequency 60 Hz |
| `ws_13579` | FFT window size (samples) |
| `tg_0` | transformation gamma 0 |
| `sm_cqt` | spectrum method (`fft` / `logfft` / `cqt`) |
| `ch_384e…` | a hash of the library configuration section |

## Versioning

Each file records the library data-version it was written with, in the metadata
that leads the file, so the version reads from the first bytes without loading
the entries. A library is derived data: its settings and the generators
determine it wholly. A library written at the version this build writes is used
as it stands, and any other is rebuilt from its settings the first time it is
needed — a conversion rebuilds it unprompted, and opening one from the
_Instructions_ tab asks first (see
[Data compatibility](../development/release/compatibility.md)).

The version therefore names what generation produces: a change to the
generators or to feature extraction bumps it, which is what has every stored
library rebuilt. Installs of different versions that share one library folder
rebuild each other's libraries as each needs them.

The current data version is 2.1.
