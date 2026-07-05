from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Final, List, Tuple

import numpy as np

from sampletones_core.audio.io import write_wave

CORPUS_SEED: Final[int] = 20260705
CORPUS_ITEM_SECONDS: Final[float] = 1.5
CORPUS_AMPLITUDE: Final[float] = 0.5

TONE_FREQUENCIES: Final[Tuple[float, ...]] = (55.0, 110.0, 220.0, 440.0, 880.0, 1760.0)
TIMBRE_DUTY_CYCLES: Final[Tuple[float, ...]] = (0.125, 0.25, 0.5)
TIMBRE_FREQUENCY: Final[float] = 220.0
MIX_TONE_FREQUENCY: Final[float] = 440.0
MIX_NOISE_LEVELS: Final[Tuple[float, ...]] = (0.05, 0.15)
SNARE_DECAY_SECONDS: Final[float] = 0.15
KICK_DECAY_SECONDS: Final[float] = 0.25
KICK_SWEEP_FREQUENCIES: Final[Tuple[float, float]] = (150.0, 50.0)
ATTACK_SECONDS: Final[float] = 0.005
ATTACK_TONE_DECAY_SECONDS: Final[float] = 0.3


@dataclass(frozen=True)
class CorpusItem:
    name: str
    category: str
    audio: np.ndarray


def build_corpus(sample_rate: int) -> List[CorpusItem]:
    """
    Synthesize the calibration probe corpus.

    The corpus spans the signal classes the criterion must arbitrate between:
    steady tones across the pitch range, pulse timbres of several duty cycles,
    broadband noise, tone-plus-noise mixes, percussive transients, and a
    crescendo probing the dynamic range. Every item is deterministic for a fixed
    sample rate, so referee scores are reproducible across runs.

    Args:
        sample_rate: Sampling rate of the synthesized items in Hz.

    Returns:
        The corpus items, each carrying its category for per-class reporting.
    """
    generator = np.random.default_rng(CORPUS_SEED)
    length = int(CORPUS_ITEM_SECONDS * sample_rate)
    time = np.arange(length) / sample_rate

    items: List[CorpusItem] = []

    for frequency in TONE_FREQUENCIES:
        audio = CORPUS_AMPLITUDE * np.sin(2.0 * np.pi * frequency * time)
        items.append(
            CorpusItem(
                name=f"tone-{frequency:g}hz",
                category="tone",
                audio=_as_wave(audio),
            ),
        )

    for duty_cycle in TIMBRE_DUTY_CYCLES:
        phase = (TIMBRE_FREQUENCY * time) % 1.0
        audio = CORPUS_AMPLITUDE * np.where(phase < duty_cycle, 1.0, -1.0)
        items.append(
            CorpusItem(
                name=f"pulse-duty{duty_cycle:g}",
                category="timbre",
                audio=_as_wave(audio),
            ),
        )

    items.append(
        CorpusItem(
            name="noise-white",
            category="noise",
            audio=_as_wave(CORPUS_AMPLITUDE * 0.5 * generator.standard_normal(length)),
        )
    )
    dark_noise = np.cumsum(generator.standard_normal(length))
    dark_noise = dark_noise - np.mean(dark_noise)
    dark_noise = dark_noise / np.max(np.abs(dark_noise))
    items.append(
        CorpusItem(
            name="noise-dark",
            category="noise",
            audio=_as_wave(CORPUS_AMPLITUDE * dark_noise),
        )
    )

    tone = CORPUS_AMPLITUDE * np.sin(2.0 * np.pi * MIX_TONE_FREQUENCY * time)
    for noise_level in MIX_NOISE_LEVELS:
        audio = tone + noise_level * generator.standard_normal(length)
        items.append(
            CorpusItem(
                name=f"mix-noise{noise_level:g}",
                category="mix",
                audio=_as_wave(audio),
            )
        )

    snare = generator.standard_normal(length) * np.exp(-time / SNARE_DECAY_SECONDS)
    items.append(
        CorpusItem(
            name="transient-snare",
            category="transient",
            audio=_as_wave(CORPUS_AMPLITUDE * snare),
        )
    )

    sweep_start, sweep_end = KICK_SWEEP_FREQUENCIES
    sweep = sweep_end + (sweep_start - sweep_end) * np.exp(-time / KICK_DECAY_SECONDS)
    kick_phase = 2.0 * np.pi * np.cumsum(sweep) / sample_rate
    kick = np.sin(kick_phase) * np.exp(-time / KICK_DECAY_SECONDS)
    items.append(CorpusItem(name="transient-kick", category="transient", audio=_as_wave(CORPUS_AMPLITUDE * kick)))

    attack = np.minimum(time / ATTACK_SECONDS, 1.0) * np.exp(-time / ATTACK_TONE_DECAY_SECONDS)
    pluck = np.sin(2.0 * np.pi * MIX_TONE_FREQUENCY * time) * attack
    items.append(CorpusItem(name="transient-pluck", category="transient", audio=_as_wave(CORPUS_AMPLITUDE * pluck)))

    crescendo = np.sin(2.0 * np.pi * MIX_TONE_FREQUENCY * time) * (time / time[-1])
    items.append(
        CorpusItem(name="dynamics-crescendo", category="dynamics", audio=_as_wave(CORPUS_AMPLITUDE * crescendo))
    )

    return items


def write_corpus(items: List[CorpusItem], directory: Path, sample_rate: int) -> Dict[str, Path]:
    """
    Write every corpus item as a WAV file.

    Args:
        items: Corpus items to write.
        directory: Target directory, created when absent.
        sample_rate: Sampling rate of the items in Hz.

    Returns:
        The written file path per item name.
    """
    directory.mkdir(parents=True, exist_ok=True)
    paths: Dict[str, Path] = {}
    for item in items:
        path = directory / f"{item.name}.wav"
        write_wave(path, sample_rate, item.audio)
        paths[item.name] = path

    return paths


def _as_wave(audio: np.ndarray) -> np.ndarray:
    clipped: np.ndarray = np.clip(audio, -1.0, 1.0)
    return clipped.astype(np.float32)
