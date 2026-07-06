# Instruction libraries

To optimize sample reconstruction, all single-oscillator instructions are prerendered as samples with spectral information.

The instruction data depends on the following configuration properties:
* `nes_frequency` (NES frequency, usually NTSC or PAL)
* `sample_rate` (in Hz)
* `transformation_gamma`, which determines the transformation of the spectral information:
    * `0` - raw absolute values of Fourier Transform
    * `100` - absolute values transformed via $\log\left(1 + x\right)$ operation

    Intermediate values interpolate between these two.

Each set of parameters corresponds to a different instructions data, encoded by a configuration key.

Libraries are generated using the generator included in the application. They can be generated from the _Instructions_ tab of the application and explored using the application.

## Data content

For each key, the data consists of single instructions. Each instruction contains:
* metadata
* instruction data
* a single waveform frame
* spectrum

### Instructions

Prerendered instructions contain the following data:
* generator class (`pulse`/`triangle`/`noise`)
* instruction data (`on`/`pitch`/`period`/`volume`/`duty_cycle`/`short`)

Instructions contain basic information for all 2A03 oscillators:
* **on** (0-1): whether a generator is on (1) or off (0)
* **pitch** (33-119) for pulse and triangle generators, and **period** (0-15) for the noise generator
* **volume** (0-15) for pulse and noise generators
* **duty_cycle** (0-3) for pulse generators, and the **short** (0-1) flag for the noise generator

### Waveform

Each instruction is prerendered as a sample containing the entire period of a wave (excluding the longest noise samples, which are trimmed to 1 second).

### Spectrum

Within each waveform, each instruction data contains spectral information on the frequency distribution in the waveform, precalculated using Fast Fourier Transform.

## File format

Instructions libraries are stored as `.ins` files in the user's documents folder, e.g.:

```
sr_44100_nf_30_ws_1615_tg_0_ch_283a31a50176c14faf36949913117e49.ins
```

The configuration is embedded in the file name:
* `sr_44100` corresponds to the sample rate 44100 Hz
* `nf_30` describes NES frequency of 30 Hz
* `ws_1615` is the size of the FFT transformation (1615 samples)
* `tg_0` encodes `transformation_gamma = 0`
* `ch_283a31a50176c14faf36949913117e49` is the config hash.
