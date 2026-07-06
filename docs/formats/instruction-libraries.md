# Instruction libraries

An instruction library is stored as a single `.ins` file holding, for every
possible instruction, the waveform its channel produces and that waveform's
[spectrum](../glossary.md#spectrum-feature-histogram). It is the catalogue the
reconstruction search draws its candidates from. For what a library is and how
it is built, see [Instruction library](../concepts/instruction-library.md); this
page documents the file.

Libraries are generated from the _Instructions_ tab (or with
`sampletones --generate`) and stored in the documents folder.

## Contents

A library is keyed by the configuration that produces it and holds one entry per
instruction.

### Per-instruction data

Each entry contains:

* **metadata** — the generator class (`pulse` / `triangle` / `noise`) and the
  instruction values below;
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
sr_44100_nf_30_ws_13579_tg_0_sm_cqt_ch_384e710987cb958adf2b214df1267d10.ins
```

| Fragment | Meaning |
| --- | --- |
| `sr_44100` | sample rate 44100 Hz |
| `nf_30` | NES frequency 30 Hz |
| `ws_13579` | FFT window size (samples) |
| `tg_0` | transformation gamma 0 |
| `sm_cqt` | spectrum method (`fft` / `logfft` / `cqt`) |
| `ch_384e…` | a hash of the full configuration |
