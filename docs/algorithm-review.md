# Algorithm review: the spectral matching criterion

A review of the reconstruction criterion — spectrum methods (FFT / LogFFT / CQT),
weighting, and their interactions — with measurements taken through the production
code, followed by a phased adaptation plan. The measurement probes live in
`tests/unit/sampletones_core/fft/spectral_probe.py`, and the behaviors documented
here are pinned by `tests/unit/sampletones_core/fft/test_spectrum_scaling.py`.

Reviewed: 2026-07-04. Gamma handling is intentionally kept as-is for now; the
gamma-related items are collected in the deferred track at the end.

---

## 1. The criterion as implemented

Per frame: `cost = α · spectral + β · temporal` (defaults 0.8 / 0.2), where

- **spectral** — weighted β-divergence (β = 1, generalized KL) between
  gamma-transformed power spectra, normalized by the target's own weighted energy:
  `Σ w·d(x, y) / (Σ w·x + ε)`. Weights = `(Δf / f_upper) · A(f)^0.5`, renormalized
  to mean 1, then a CQT-only reliability mask. Because the weights appear in both
  the numerator and the denominator, a global rescaling of the weights cancels in
  the ratio (up to the `ε` floor term); the weights matter through their *shape*
  over frequency, not their overall scale.
- **temporal** — unweighted, un-normalized RMSE between phase-aligned waveforms.
- **gamma transform** — Yeo-Johnson `((x + ε)^λ − ε^λ) / λ`, λ = 1 − γ/100,
  ε = `SPECTRUM_FLOOR` = (1/15)² ≈ 4.4e-3. γ = 0 (identity) is the default;
  intermediate γ is currently unavailable (README caveat).

---

## 2. Measurements

The tables record the behavior *at review time* (pre-Phase-1). Phase 1 unified the
tone convention to `A²/2` for every method and normalized the windowed spectra by
the envelope energy gain, so the FFT/LogFFT tone rows now read `2×` these values
and stay constant across NES frequencies; the structural facts are unchanged.

### 2.1 Tone and noise response per method

44.1 kHz, NES frequency 30 (window 1615, frame 1470); tone amplitude 0.5
(band energy = sum over ±2 bins around the tone), noise σ = 0.1 (single bin,
averaged over draws):

|                   | 110 Hz tone | 440   | 1.76k | 7.04k | noise @110 | @440   | @1.76k | @7.04k |
| ----------------- | ----------- | ----- | ----- | ----- | ---------- | ------ | ------ | ------ |
| FFT               | 0.062       | 0.062 | 0.057 | 0.061 | 4.8e-6     | 7.2e-6 | 5.2e-6 | 6.0e-6 |
| LogFFT            | **0.026**   | 0.061 | 0.061 | 0.062 | 1.2e-6     | 6.8e-6 | 2.1e-5 | 9.3e-5 |
| CQT               | 0.193       | 0.193 | 0.193 | 0.192 | 3.6e-6     | 1.7e-5 | 8.8e-5 | 2.6e-4 |

Structural facts:

- **Tones are intensive** — constant per bin on every axis. Exact conventions,
  measured with bin-centered tones: an FFT bin reports `(A/2)²`, a CQT bin
  reports `A²/2` — a factor-2 difference in single-bin convention (≈3× in ±2-bin
  band energy, since constant-Q neighbors overlap).
- **Noise is extensive on the log axes** — per-bin value ∝ bin bandwidth ∝ f
  (~+3 dB/octave), while it reads flat per bin on the linear axis.
- **LogFFT smears low tones** — a 110 Hz tone retains only ~0.43× of its band
  energy within ±2 bins; the rebinning spreads it over log bins narrower than the
  FFT resolution (§4.3).

### 2.2 Per-octave weight allocation

Share of total criterion weight per octave (`perceptual_exponent = 0.5`):

| axis   | 55–110 | 110–220 | 220–440 | 440–880 | 880–1.76k | 1.76–3.52k | 3.52–7.04k | 7.04–14.1k |
| ------ | ------ | ------- | ------- | ------- | --------- | ---------- | ---------- | ---------- |
| FFT    | 0.038  | 0.064   | 0.096   | 0.127   | 0.148     | 0.156      | 0.149      | 0.125      |
| LogFFT | 0.042  | 0.070   | 0.104   | 0.135   | 0.155     | 0.161      | 0.141      | 0.129      |
| CQT    | 0.043  | 0.071   | 0.104   | 0.135   | 0.155     | 0.161      | 0.153      | 0.127      |

The density term `Δf / f_upper` converts every axis to a common log-frequency
measure, so the allocation is method-uniform by construction — verified above.
Bin *granularity* still differs (2 bins vs 12 bins in the bottom octave).

### 2.3 Window scaling (frame-length dependence)

44.1 kHz across NES frequencies. FFT/LogFFT keep the window at
`max(frame_length, 2·sample_rate/55 Hz)` = 1615 for NES ≥ 28 Hz; the Tukey taper
share is `1 − frame/window`:

| NES freq | frame | window | taper share | FFT tone @440 | FFT noise @440 | CQT tone @440 |
| -------- | ----- | ------ | ----------- | ------------- | -------------- | ------------- |
| 15       | 2940  | 2940   | 0 %         | 0.059         | 3.4e-6         | 0.193         |
| 30       | 1470  | 1615   | 9 %         | 0.058         | 7.6e-6         | 0.193         |
| 60       | 735   | 1615   | 54 %        | 0.040         | 3.4e-6         | 0.193         |
| 120      | 368   | 1615   | 77 %        | 0.032         | 2.9e-6         | 0.193         |
| 300      | 147   | 1615   | 91 %        | 0.027         | 2.0e-6         | 0.192         |

Findings (see §5 for interpretation):

- **FFT/LogFFT responses scale with the envelope energy gain** `mean(envelope²)`
  — measured tone ratio 0.44 between NES 300 and 30 vs predicted 0.457. Tone and
  per-bin noise scale by the *same* factor, so tone-vs-noise proportions are
  preserved; the drift is in the absolute scale (~3.6 dB across NES 30 → 300).
- **CQT is frame-length invariant** — wavelet lengths depend on frequency alone;
  the frame length only positions the columns.
- **Per-octave weight shares are window-invariant** (only a small granularity
  effect at NES 15, where Δf halves).
- Below NES ≈ 28 the window grows with the frame (zero taper, pure rectangular
  analysis); per-bin FFT noise then additionally falls as 1/window while tones
  stay constant — the expected behavior of finer resolution, absorbed by the
  density weighting.

---

## 3. The four review questions

### 3.1 Is there a sound metric more aligned with perception?

The current design is already architecturally close to a loudness model:
β-divergence on band energies over a log axis with an audibility weight is a
crude Zwicker/Moore pipeline. The gap is calibration, not architecture. In order
of perceptual importance:

1. **Auditory frequency axis.** Critical bands follow the ERB scale,
   `ERB(f) = 24.7·(4.37·f/1000 + 1)`: ≈ log above ~500 Hz (the CQT axis is right
   there), ~constant-width below. Pure log therefore over-resolves and
   over-weights the bass: at 100 Hz one ERB ≈ 36 Hz ≈ 6 semitones, so 12
   bins/octave places ~6 equally-weighted bins inside one critical band, giving
   the bottom two octaves roughly 2–3× the weight perception assigns them.
2. **Compressive per-band nonlinearity.** Specific loudness goes as
   (band energy)^0.23–0.3 (Stevens; Moore–Glasberg). This maps exactly onto the
   gamma knob: γ ≈ 70–77 gives λ ≈ 0.23–0.3. Deferred with the gamma track.
3. **Level-appropriate weighting.** A-weighting is the 40-phon (near-threshold)
   contour and over-attenuates bass at music listening levels; the 0.5 exponent
   is an uncalibrated softener. Principled replacements: **K-weighting**
   (ITU-R BS.1770, the LUFS filter) or an inverse **ISO 226:2023** contour at
   ~70–80 phon.
4. **Simultaneous masking.** An error next to a loud partial is inaudible; the
   same error in a quiet region is glaring. The cheap classic is noise-to-mask
   ratio (PEAQ's core): derive a masking threshold from the target frame
   (spreading function over the ERB/Bark axis), weight per-bin error by
   1/threshold. Candidate-independent, so it fits the existing broadcasting
   shape. This is the natural next-generation criterion.
5. **Full perceptual models** (PEMO-Q, ViSQOL v3, CDPAM, Zimtohrli) are too heavy
   for the inner loop and partly out-of-domain for chiptune; their role is as
   offline calibration referees (§6, Phase 4).

The (γ, divergence-β) knobs are nearly redundant: locally
`d_β(x, y) ≈ (x − y)²·y^(β−2)/2`, so β = 2 is squared error, β = 1 ≈ squared
error on √-compressed values, β = 0 (Itakura–Saito) ≈ squared error on log
values. One knob should own compression; the other should be fixed by its
asymmetry/robustness semantics.

The temporal term is absolute while the spectral term is relative, so the
effective α/β mix drifts with frame loudness — temporal dominates loud frames,
spectral dominates quiet ones. Normalizing the temporal RMSE by the target frame
RMS makes the blend level-stable.

### 3.2 Is the FFT biased toward high frequencies because of bin density?

Raw FFT: yes — any unweighted per-bin sum is dominated by the top octaves
(2 vs 258 bins per octave at the extremes). In the criterion: no — the density
weight cancels the mass bias exactly (§2.2). What remains and cannot be fixed by
weighting:

- **Resolution, not mass.** A semitone at 110 Hz (6.4 Hz) is invisible against
  Δf ≈ 27.3 Hz; low-pitch candidates within ±2 semitones produce near-identical
  FFT features, so low-pitch selection falls to the temporal term and upper
  harmonics.
- **Leakage.** The near-rectangular window (9% taper at NES 30) has ~−13 dB
  first sidelobes; at γ = 100 log compression elevates the skirts. Library
  references are phase-averaged (smooth leakage) while the target is
  single-phase — a mild asymmetry.
- **Broadband allocation** differs from the log axes (§4.2).

### 3.3 Weighting inventory

| # | Weight | Applies to | Verdict |
| - | ------ | ---------- | ------- |
| 1 | Density `Δf/f_upper` (≈ d(log f)) | all methods | Justified as octave-uniform allocation; verified uniform across methods. Pure log over-weights < 500 Hz relative to ERB |
| 2 | `A(f)^0.5` | all methods | Right intent, wrong calibration: 40-phon contour, ad-hoc exponent; multiplies whatever units γ produces (power errors at γ = 0, dB-like errors at γ = 100) |
| 3 | Mean-1 renormalization | all | Hygiene only: weight scale cancels in the spectral ratio except through the `ε` floor term |
| 4 | CQT reliability mask | CQT | Principled (a bin counts only when its wavelet fits the signal); scale effects cancel in the ratio, the substantive effect is that under-resolved low bins carry no evidence |
| 5 | Target-energy denominator | spectral | Makes matching about shape; source of the α/β level drift (§3.1) |
| 6 | Temporal: flat, unweighted | temporal | Implicitly flat-spectrum; acceptable as a tiebreaker once RMS-normalized |
| 7 | γ transform + `SPECTRUM_FLOOR` | value domain | Weightings too: γ re-weights quiet vs loud detail; the floor mutes everything below (1/15)² (§4.6) |

Upgrades: ERB density (`Δf/ERB(f)`, converging to the current measure above
500 Hz) and K-weighting in place of `A^0.5` — both localized in
`sampletones_core/fft/fft.py`. Masking-based weights are the larger,
target-adaptive step.

### 3.4 Hidden biases across methods

1. **Scale conventions differ ~2×** (FFT `(A/2)²` vs CQT `A²/2` per
   bin-centered tone, measured). The shared `SPECTRUM_FLOOR` therefore sits at a
   different relative level per method, shifting the γ = 100 curve and the
   β-divergence asymmetry point.
2. **Tone-intensive vs noise-extensive semantics.** Broadband noise reads
   +3 dB/octave per bin on log axes, flat on the linear axis; after weighting,
   the same noise contributes a flat per-octave profile under FFT and a rising
   one under LogFFT/CQT. Above ~500 Hz the log-axis behavior is the perceptually
   correct one (critical-band noise loudness grows with bandwidth), but the
   practical consequence stands: **switching spectrum method re-balances the
   tonal-vs-noise channel competition** and needs empirical calibration.
3. **LogFFT pseudo-resolution.** The CDF rebin spreads sub-resolution tones over
   several correlated log bins (110 Hz keeps ~0.43× of its band energy); low
   tones masquerade as broadband. Mitigation: floor the log-bin width at Δf, or
   treat LogFFT as legacy now that the CQT exists.
4. **CQT temporal smearing.** The 55 Hz wavelet spans ~0.31 s; low-bin emissions
   blend that much context, onsets pre-echo, and attack levels under-read against
   steady-state references. Viterbi transition costs currently absorb the smear,
   so transition tuning is entangled with the spectrum method — and, since the
   smear measured *in frames* is proportional to the NES frequency (4.6 frames at
   15 Hz, 93 at 300 Hz), with the frame rate as well.
5. **CQT edge bias.** Zero padding under-reads low bins in the first/last
   ~0.15 s of the signal.
6. **β-divergence asymmetry vs its documentation.** With β = 1 and ε = 4.4e-3, a
   missing target bin of value v costs ≈ `v·ln(v/ε) − v` while a spurious bin of
   the same size costs ≈ v; the crossover is v = ε·e² ≈ 0.033. For meaningful
   partials (measured 0.06–0.19) **omitting energy costs ~2× more than adding
   it** — opposite to the claim in `docs/algorithms.md` §4. The asymmetry
   direction is an accidental function of `SPECTRUM_FLOOR`, which simultaneously
   anchors the γ log transition — one constant, two unrelated roles.
7. **Reference averaging domain differs per method** at γ > 0:
   `WindowedFeatureExtractor` averages phases in feature space,
   `CQTFeatureExtractor` averages columns in power space (Jensen gap). Deferred
   with the gamma track; identical at γ = 0.
8. Housekeeping: `InstructionsLibraryConfig.spectrum_method` defaults to `CQT`
   while `docs/algorithms.md` still names `fft` as the default;
   `Window.weights` / `calculate_weights` (the 1/f · A¹ variant) have no
   remaining consumers.

---

## 5. Window scaling: are proportions preserved across frame lengths?

Mostly yes — with one systematic exception on the windowed axes.

- **Preserved:** per-octave weight shares (§2.2 holds at every window size); CQT
  responses (fully frame-length invariant); tone-vs-noise *proportions* under
  FFT/LogFFT (both scale by the same envelope energy gain).
- **Drifting:** the *absolute* FFT/LogFFT response scales with
  `mean(envelope²)`, falling ~2.3× (3.6 dB) from NES 30 to NES 300 as the taper
  share grows from 9% to 91%. Since `SPECTRUM_FLOOR` and the working level are
  fixed, the effective volume floor, the β-divergence asymmetry crossover (§3.4.6)
  and the γ = 100 curvature all shift with the frame rate. Within one
  configuration both target and candidates share the window, so candidate
  *ranking* is affected only through these floor interactions — the first-order
  problem is cross-configuration semantics, not within-frame ordering.
- **Two further frame-rate couplings:** at high NES frequencies the fixed window
  spans several frames (±5 at 300 Hz), so FFT features carry taper-weighted
  context from neighboring frames — a milder, frequency-independent analogue of
  the CQT smear; and under CQT the smear measured in frames grows with the NES
  frequency (§3.4.4), coupling Viterbi tuning to the frame rate.

The Phase 1 fix is to normalize the windowed spectra by the envelope energy gain,
making the response frame-rate invariant (`mean(envelope²) = 1` reproduces
today's values at zero taper, so NES ≤ 28 behavior is unchanged).

---

## 6. Adaptation plan

Each phase is independently shippable. "Regen" marks phases that change stored
library features and therefore require regenerating instruction libraries (the
config hash key changes with them).

### Phase 0 — measurement infrastructure — DONE (2026-07-04)

- This document.
- `SpectrumProbe` + helpers in `tests/unit/sampletones_core/fft/spectral_probe.py`.
- Characterization tests in `tests/unit/sampletones_core/fft/test_spectrum_scaling.py`
  pinning: tone flatness per method, noise-bandwidth scaling, cross-method weight
  allocation, window-scaling laws, and the per-method scale conventions. Tests
  that pin a bias slated for removal (envelope-gain drift, LogFFT smearing,
  2× convention gap) are updated deliberately in the phase that removes it.

### Phase 1 — scale normalization (regen) — DONE (2026-07-04)

Goal: one tone convention, frame-rate-invariant response, level-stable loss mix.

Landed as: one-sided FFT power spectrum (`calculate_fft_spectrum`),
`Window.energy_gain` + normalization in `WindowedFeatureExtractor._windowed_feature`,
RMS normalization in `Criterion.temporal_loss` floored by the configurable
`metric.temporal_level_floor`, and the `algorithms.md` fixes (asymmetry direction,
temporal term, default method, shared scale convention). Stored library features
changed, so libraries are regenerated manually; the data version stays `1.1`
because that value has never shipped.

Review follow-up: algorithm policy constants moved from `constants/general.py` to
`constants/algorithm.py` (hardware and music facts remain in `general.py`; the
unused `BATCH_SIZE` was dropped), and the tuning knobs worth adapting joined their
config units — `metric.temporal_level_floor`, `general.quantization_levels`,
`general.coefficient_percentile`, `general.coefficient_audibility_floor` — all
serialized through the existing `config.json`, keeping a single configuration
source of truth.

1. Normalize FFT/LogFFT spectra by the envelope energy gain `mean(envelope²)`
   at feature-extraction time, making the response independent of the taper
   share (§5). Zero-taper configurations are numerically unchanged.
2. Unify the tone convention across methods (align FFT's `(A/2)²` and CQT's
   `A²/2` to a single choice; `A²/2` equals the tone's mean-square power and is
   the physically natural one).
3. Normalize the temporal RMSE by the target frame RMS (floored by
   `MINIMUM_AUDIO_LEVEL`) so the α/β blend is level-independent.
4. Re-derive `SPECTRUM_FLOOR` consequences under the unified scale and document
   the intended β-divergence asymmetry direction (fixing the `algorithms.md`
   claim); an explicit asymmetry constant separate from the γ anchor can wait
   for the gamma track.
5. Update Phase 0 tests: envelope-gain drift and the 2× convention tests tighten
   into invariance assertions.

### Phase 2 — perceptual weighting (no regen)

Weights live only in `Criterion`, so libraries are untouched.

1. Replace the density term with ERB density `Δf/ERB(f)` in
   `calculate_weights_from_edges`.
2. Replace `A(f)^0.5` with K-weighting (ITU-R BS.1770); keep
   `perceptual_exponent` as the intensity knob applied to the new curve, or
   introduce a `weighting` enum in `MetricConfig` if both curves should remain
   selectable.
3. Validate with the probe tests (weight-share table changes shape by design —
   update the pinned shares) and an A/B reconstruction listen on a small corpus.

### Phase 3 — LogFFT low end (regen, LogFFT only)

Floor the log-bin width at the FFT resolution Δf (merge sub-resolution bins), so
low tones stay compact and bins remain statistically independent. If LogFFT
usage does not justify the work, document it as a legacy axis instead and point
users at CQT.

### Phase 4 — calibration harness (offline tooling)

A script (under `scripts/`) that:

1. Builds a synthetic probe corpus: single tones per pitch, each noise period,
   duty-cycle timbres, tone+noise mixes, transients.
2. Reconstructs the corpus under each spectrum method and NES frequency.
3. Scores results with an external perceptual referee (Zimtohrli / ViSQOL /
   PEMO-Q) and reports selected-instruction confusion tables per method.
4. Sweeps α/β, `perceptual_exponent`, and the Viterbi transition weights —
   per spectrum method and per NES frequency, since §5 couples both to the
   effective smear.

### Deferred — gamma track

Kept out of scope for now, collected for later: intermediate-gamma fix and a
loudness-exponent default (γ ≈ 70); unifying the reference-averaging domain
(§3.4.7); decoupling the divergence asymmetry constant from the γ log anchor;
masking-based (NMR) per-frame weights, which operate in the γ feature space and
should follow the gamma decisions.

---

## Sources

- [Zimtohrli: An Efficient Psychoacoustic Audio Similarity Metric](https://arxiv.org/html/2509.26133)
- ITU-R BS.1770 (K-weighting / LUFS); ISO 226:2023 (equal-loudness contours);
  ISO 532 (Zwicker / Moore–Glasberg loudness); Glasberg & Moore (ERB scale);
  ITU-R BS.1387 PEAQ (noise-to-mask ratio); Yamamoto et al., Parallel WaveGAN
  (multi-resolution STFT loss).
