from dataclasses import dataclass
from typing import Dict, Final, List, Type, Union

import numpy as np
import pytest

from sampletones_core.configs import Config
from sampletones_core.constants.algorithm import MINIMUM_AUDIO_LEVEL
from sampletones_core.constants.enums import DEFAULT_CHANNELS, ChannelName, GeneratorClassName, LevelMethod
from sampletones_core.fft import Window
from sampletones_core.generators import FULL_SCALE_RMS_LEVELS, GeneratorUnion
from sampletones_core.reconstructions.reconstructor.level.working import FittedLevel, LoudnessLevel, working_level
from sampletones_core.reconstructions.reconstructor.matching import FrameMatcher
from sampletones_core.reconstructions.reconstructor.stems.configs.config import StemsConfig
from sampletones_core.reconstructions.reconstructor.stems.configs.settings import StemSettings
from sampletones_core.reconstructions.reconstructor.worker import ReconstructorWorker
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase

TRIANGLE_LEVEL: Final[float] = FULL_SCALE_RMS_LEVELS[GeneratorClassName.TRIANGLE_GENERATOR]
STEADY_LEVEL: Final[float] = 0.5
QUIET_LEVEL: Final[float] = 0.1
LOUD_LEVEL: Final[float] = 0.9
TRANSIENT_LEVEL: Final[float] = 1.0
BED_LEVEL: Final[float] = 0.05
SILENCE: Final[float] = 0.0
BED_FRAMES: Final[int] = 24
SINE_FRAMES: Final[int] = 30
SINE_AMPLITUDE: Final[float] = 0.8
SINE_CYCLES_PER_FRAME: Final[int] = 4
ONE_FRAME: Final[int] = 1


@pytest.fixture(name="loudness")
def loudness_fixture(config: Config, channels: Dict[ChannelName, GeneratorUnion]) -> LoudnessLevel:
    return LoudnessLevel(config, channels)


@pytest.fixture(name="matcher")
def matcher_fixture(worker: ReconstructorWorker) -> FrameMatcher:
    return worker.matcher


@pytest.fixture(name="full_setup")
def full_setup_fixture() -> StemsConfig:
    return _covering(list(DEFAULT_CHANNELS))


def _covering(channels: List[ChannelName]) -> StemsConfig:
    return StemsConfig.single_entry(StemSettings.covering(channels))


def _steady(config: Config, level: float, frames: int) -> np.ndarray:
    return np.full(config.library.frame_length * frames, level, dtype=np.float32)


class TestTheLoudnessLevel:
    def test_uniform_audio_anchors_to_its_level(
        self, config: Config, loudness: LoudnessLevel, full_setup: StemsConfig, matcher: FrameMatcher
    ) -> None:
        coefficient = loudness.coefficient([_steady(config, STEADY_LEVEL, ONE_FRAME)], full_setup, matcher)

        assert coefficient == pytest.approx(STEADY_LEVEL / TRIANGLE_LEVEL)

    def test_coefficient_is_robust_to_a_lone_transient(
        self, config: Config, loudness: LoudnessLevel, full_setup: StemsConfig, matcher: FrameMatcher
    ) -> None:
        audio = _steady(config, BED_LEVEL, BED_FRAMES)
        audio[: config.library.frame_length] = TRANSIENT_LEVEL

        coefficient = loudness.coefficient([audio], full_setup, matcher)

        assert coefficient == pytest.approx(BED_LEVEL / TRIANGLE_LEVEL, rel=1e-3)
        assert coefficient < TRANSIENT_LEVEL / TRIANGLE_LEVEL

    def test_louder_audio_produces_larger_coefficient(
        self, config: Config, loudness: LoudnessLevel, full_setup: StemsConfig, matcher: FrameMatcher
    ) -> None:
        quiet = loudness.coefficient([_steady(config, QUIET_LEVEL, ONE_FRAME)], full_setup, matcher)
        loud = loudness.coefficient([_steady(config, LOUD_LEVEL, ONE_FRAME)], full_setup, matcher)

        assert loud > quiet

    def test_a_steady_sine_lands_at_the_level_a_full_volume_triangle_plays(
        self, config: Config, loudness: LoudnessLevel, full_setup: StemsConfig, matcher: FrameMatcher
    ) -> None:
        frame_length = config.library.frame_length
        phase = np.arange(frame_length * SINE_FRAMES) * SINE_CYCLES_PER_FRAME / frame_length
        sine = (SINE_AMPLITUDE * np.sin(2.0 * np.pi * phase)).astype(np.float32)

        scaled = sine / loudness.coefficient([sine], full_setup, matcher)

        level = float(np.sqrt(np.mean(np.square(scaled.astype(np.float64)))))
        assert level == pytest.approx(TRIANGLE_LEVEL, rel=1e-2)

    def test_a_silent_recording_is_read_at_the_least_level(
        self, config: Config, loudness: LoudnessLevel, full_setup: StemsConfig, matcher: FrameMatcher
    ) -> None:
        coefficient = loudness.coefficient([_steady(config, SILENCE, BED_FRAMES)], full_setup, matcher)

        assert coefficient == pytest.approx(MINIMUM_AUDIO_LEVEL / TRIANGLE_LEVEL)

    def test_the_level_is_read_on_the_recordings_mix(
        self, config: Config, loudness: LoudnessLevel, full_setup: StemsConfig, matcher: FrameMatcher
    ) -> None:
        half = _steady(config, STEADY_LEVEL / 2, ONE_FRAME)

        coefficient = loudness.coefficient([half, half], full_setup, matcher)

        assert coefficient == pytest.approx(STEADY_LEVEL / TRIANGLE_LEVEL)


class TestTheLoudnessLevelFollowsTheCoveredChannels(BaseTestSuite):
    """The loudness level is brought to the full-scale RMS level of the quietest tone channel a setup covers."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        channels: List[ChannelName]
        anchor: GeneratorClassName

    test_cases = (
        TestCase(
            label="triangle_among_the_tone_channels",
            channels=[ChannelName.PULSE1, ChannelName.TRIANGLE, ChannelName.NOISE],
            anchor=GeneratorClassName.TRIANGLE_GENERATOR,
        ),
        TestCase(
            label="pulse_without_the_triangle",
            channels=[ChannelName.PULSE1, ChannelName.NOISE],
            anchor=GeneratorClassName.PULSE_GENERATOR,
        ),
        TestCase(
            label="noise_without_a_tone_channel",
            channels=[ChannelName.NOISE],
            anchor=GeneratorClassName.NOISE_GENERATOR,
        ),
    )

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_the_level_follows_the_covered_channels(
        self, config: Config, loudness: LoudnessLevel, matcher: FrameMatcher, test_case: TestCase
    ) -> None:
        coefficient = loudness.coefficient(
            [_steady(config, STEADY_LEVEL, ONE_FRAME)], _covering(test_case.channels), matcher
        )

        assert coefficient == pytest.approx(STEADY_LEVEL / FULL_SCALE_RMS_LEVELS[test_case.anchor])


class TestTheWorkingLevelAConfigurationNames(BaseTestSuite):
    """Each level method names the working level a run matches at."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        method: LevelMethod
        level: Union[Type[LoudnessLevel], Type[FittedLevel]]

    test_cases = (
        TestCase(label="coefficient_by_the_frames_loudness", method=LevelMethod.COEFFICIENT, level=LoudnessLevel),
        TestCase(label="fitted_onto_a_triangle_line", method=LevelMethod.FITTED, level=FittedLevel),
    )

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_the_method_names_its_level(
        self,
        config: Config,
        window: Window,
        channels: Dict[ChannelName, GeneratorUnion],
        test_case: TestCase,
    ) -> None:
        configured = config.model_copy(
            update={"general": config.general.model_copy(update={"level": test_case.method})}
        )

        assert type(working_level(configured, channels, window)) is test_case.level

    def test_the_fitted_level_starts_from_the_loudness_level(
        self, config: Config, window: Window, channels: Dict[ChannelName, GeneratorUnion]
    ) -> None:
        fitted = config.model_copy(update={"general": config.general.model_copy(update={"level": LevelMethod.FITTED})})

        level = working_level(fitted, channels, window)

        assert isinstance(level, FittedLevel)
        assert type(level.loudness) is LoudnessLevel
