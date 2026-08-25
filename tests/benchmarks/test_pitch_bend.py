from pathlib import Path
from time import process_time
from typing import Final, List

import numpy as np
import pytest

from sampletones_core.audio import write_wave
from sampletones_core.configs import Config
from sampletones_core.configs.generation import GenerationConfig, RefinementConfig
from sampletones_core.constants.enums import ChannelName
from sampletones_core.generators.render import render_instructions
from sampletones_core.instructions import PulseInstruction
from sampletones_core.reconstructions import Reconstructor
from tests.integration.assets.reconstruction import build_mini_library

FRAMES: Final[int] = 6000
PITCH: Final[int] = 60
VOLUME: Final[int] = 12
REPEATS: Final[int] = 3
BEND_OVERHEAD_LIMIT: Final[float] = 1.25
REFINEMENT_OVERHEAD_LIMIT: Final[float] = 1.20
CONVERSION_SECONDS: Final[float] = 2.0
LOWER_TONE: Final[float] = 261.0
UPPER_TONE: Final[float] = 393.0
NOISE_LEVEL: Final[float] = 0.05
NOISE_SEED: Final[int] = 23


def _stream(bent: bool) -> List[PulseInstruction]:
    """One channel's frames, every one of them bent or none of them."""
    return [
        PulseInstruction(
            on=True,
            pitch=PITCH,
            volume=VOLUME,
            duty_cycle=frame % 4,
            detune=(frame % 21) - 10 if bent else 0,
        )
        for frame in range(FRAMES)
    ]


def _render_seconds(config: Config, instructions: List[PulseInstruction]) -> float:
    """The best of several renders, which is the reading least disturbed by other load."""
    readings: List[float] = []
    for _ in range(REPEATS):
        started = process_time()
        render_instructions(instructions, ChannelName.PULSE1, config)
        readings.append(process_time() - started)

    return min(readings)


@pytest.fixture(scope="module")
def config() -> Config:
    return Config()


class TestBendingCostsNothingToRender:
    """A bend moves the divider a frame loads, which is the same work as loading it unbent.

    The reading is a ratio against the same render without a bend, since what a machine renders
    a frame in is its own. What the bound catches is a bend that made rendering a different
    kind of work — a per-frame table rebuild, a lost cache, a fallback path.
    """

    def test_a_bent_stream_renders_in_what_an_unbent_one_takes(self, config: Config) -> None:
        unbent = _render_seconds(config, _stream(bent=False))
        bent = _render_seconds(config, _stream(bent=True))

        assert bent < unbent * BEND_OVERHEAD_LIMIT, f"unbent {unbent:.4f}s, bent {bent:.4f}s"


def _conversion_config(*, refining: bool) -> Config:
    return Config(generation=GenerationConfig(refinement=RefinementConfig(enabled=refining)))


def _target(path: Path, config: Config) -> Path:
    """A two-tone target under light noise, which is the shape a conversion works hardest on."""
    sample_rate = config.library.sample_rate
    count = int(sample_rate * CONVERSION_SECONDS)
    time = np.arange(count) / sample_rate
    audio = 0.5 * np.sin(2 * np.pi * LOWER_TONE * time) + 0.3 * np.sin(2 * np.pi * UPPER_TONE * time)
    audio += np.random.default_rng(NOISE_SEED).normal(0.0, NOISE_LEVEL, count)

    write_wave(path, sample_rate, audio)
    return path


def _conversion_seconds(config: Config, audio_path: Path) -> float:
    """The best of several conversions of the same target, library build excluded."""
    library = build_mini_library(config)
    readings: List[float] = []
    for _ in range(REPEATS):
        started = process_time()
        Reconstructor(config, library=library)(audio_path)
        readings.append(process_time() - started)

    return min(readings)


class TestRefiningCostsLittleOnTopOfAConversion:
    """The refinement reads a phase the transform already carries, over a handful of harmonics.

    It enumerates no candidate and rescores nothing, so what it adds to a conversion is one more
    transform per recording and a small walk per channel. The reading is a ratio against the same
    conversion with the refinement off, since what a machine converts a second of audio in is its
    own; what the bound catches is a refinement that started doing the matching's kind of work.
    """

    def test_a_refined_conversion_costs_about_what_a_plain_one_costs(self, tmp_path: Path) -> None:
        plain = _conversion_config(refining=False)
        audio_path = _target(tmp_path / "target.wav", plain)

        unrefined = _conversion_seconds(plain, audio_path)
        refined = _conversion_seconds(_conversion_config(refining=True), audio_path)

        assert refined < unrefined * REFINEMENT_OVERHEAD_LIMIT, f"unrefined {unrefined:.3f}s, refined {refined:.3f}s"
