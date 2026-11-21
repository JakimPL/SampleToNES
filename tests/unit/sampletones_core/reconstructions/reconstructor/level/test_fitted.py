from typing import Dict, Final, List, Tuple

import numpy as np
import pytest

from sampletones_core.configs import Config
from sampletones_core.constants.enums import ChannelName
from sampletones_core.fft import Window
from sampletones_core.generators import GeneratorUnion, render_instructions
from sampletones_core.instructions import InstructionUnion, PulseInstruction, TriangleInstruction
from sampletones_core.reconstructions.reconstructor.level import (
    FrameReading,
    LevelFitter,
    LevelReading,
    StandingFrame,
    fitted,
)
from sampletones_core.reconstructions.reconstructor.matching import FrameMatcher
from sampletones_core.reconstructions.reconstructor.stems.configs.config import StemsConfig
from sampletones_core.reconstructions.reconstructor.stems.configs.settings import StemSettings

from ..conftest import rendered_audio

LEVEL: Final[float] = 0.6
NOTE: Final[int] = 48
BASS: Final[TriangleInstruction] = TriangleInstruction(on=True, pitch=NOTE)
LEAD: Final[PulseInstruction] = PulseInstruction(on=True, pitch=64, volume=12, duty_cycle=2)
LOW_PULSE: Final[PulseInstruction] = PulseInstruction(on=True, pitch=48, volume=15, duty_cycle=2)
HELD_FRAMES: Final[int] = 32
DETACHED_NOTE_FRAMES: Final[int] = 3
REST_FRAMES: Final[int] = 3
LEVEL_TOLERANCE: Final[float] = 0.05
EVERY_CHANNEL: Final[List[ChannelName]] = ChannelName.items()
PULSES: Final[List[ChannelName]] = [ChannelName.PULSE1, ChannelName.PULSE2]
TRIANGLE_ONLY: Final[List[ChannelName]] = [ChannelName.TRIANGLE]


def _reading(levels: Tuple[float, ...], sampled: int) -> LevelReading:
    standing = tuple(
        StandingFrame(stem_id=0, index=index, reading=FrameReading(level=level, note=NOTE))
        for index, level in enumerate(levels)
    )
    return LevelReading(sampled=sampled, standing=standing)


class TestTheLevelTheFramesAgreeOn:
    def test_frames_agreeing_on_a_triangle_line_give_its_level(self) -> None:
        frames = 2 * fitted.LEAST_STANDING_FRAMES

        assert _reading((LEVEL,) * frames, frames).level == pytest.approx(LEVEL)

    def test_a_bass_reading_quieter_or_louder_on_some_frames_is_read_where_the_most_frames_agree(self) -> None:
        frames = 4 * fitted.LEAST_STANDING_FRAMES
        strays = {0: 0.85, 1: 1.15}
        levels = tuple(LEVEL * strays.get(index % 4, 1.0) for index in range(frames))

        assert _reading(levels, frames).level == pytest.approx(LEVEL)

    def test_too_few_frames_with_a_triangle_line_give_no_level(self) -> None:
        frames = fitted.LEAST_STANDING_FRAMES - 1

        assert _reading((LEVEL,) * frames, frames).level is None

    def test_a_triangle_line_holding_too_small_a_share_of_the_frames_gives_no_level(self) -> None:
        standing = fitted.LEAST_STANDING_FRAMES
        sampled = int(np.ceil(standing / fitted.LEAST_STANDING_SHARE)) + 1

        assert _reading((LEVEL,) * standing, sampled).level is None

    def test_readings_scattered_wider_than_the_spread_allowed_give_no_level(self) -> None:
        frames = 2 * fitted.LEAST_STANDING_FRAMES
        wide = 2.0 * fitted.MOST_SPREAD
        levels = tuple(LEVEL * (1.0 + wide * (index % 2 - 0.5)) for index in range(frames))

        assert _reading(levels, frames).level is None


def _fitter(
    channels: List[ChannelName],
    config: Config,
    window: Window,
    all_channels: Dict[ChannelName, GeneratorUnion],
    joint_matcher: FrameMatcher,
) -> LevelFitter:
    stems = StemsConfig.single_entry(StemSettings.covering(channels))
    return LevelFitter(stems, all_channels, joint_matcher, config, window)


def _held(config: Config, notes: Dict[ChannelName, InstructionUnion]) -> np.ndarray:
    return rendered_audio(config, notes, HELD_FRAMES)


def _detached(config: Config) -> np.ndarray:
    """The bass played in short notes with rests between them, over as many frames as a held note."""
    period = [BASS] * DETACHED_NOTE_FRAMES + [TriangleInstruction.null_instruction()] * REST_FRAMES
    frames = (period * (HELD_FRAMES // len(period) + 1))[:HELD_FRAMES]
    return render_instructions(frames, ChannelName.TRIANGLE, config)


class TestFittingTheWorkingLevel:
    def test_a_held_bass_under_a_lead_moves_the_level_onto_the_triangle(
        self,
        config: Config,
        window: Window,
        all_channels: Dict[ChannelName, GeneratorUnion],
        joint_matcher: FrameMatcher,
    ) -> None:
        fitter = _fitter(EVERY_CHANNEL, config, window, all_channels, joint_matcher)
        recording = _held(config, {ChannelName.TRIANGLE: BASS, ChannelName.PULSE1: LEAD})

        factor = fitter.factor({0: recording}, 1.0 / LEVEL)

        assert factor == pytest.approx(LEVEL, rel=LEVEL_TOLERANCE)

    def test_a_low_pulse_a_triangle_would_only_stand_in_for_keeps_the_level(
        self,
        config: Config,
        window: Window,
        all_channels: Dict[ChannelName, GeneratorUnion],
        joint_matcher: FrameMatcher,
    ) -> None:
        fitter = _fitter(EVERY_CHANNEL, config, window, all_channels, joint_matcher)

        assert fitter.factor({0: _held(config, {ChannelName.PULSE1: LOW_PULSE})}, 1.0) is None

    def test_a_setup_without_the_triangle_keeps_the_level(
        self,
        config: Config,
        window: Window,
        all_channels: Dict[ChannelName, GeneratorUnion],
        joint_matcher: FrameMatcher,
    ) -> None:
        fitter = _fitter(PULSES, config, window, all_channels, joint_matcher)

        assert fitter.factor({0: _held(config, {ChannelName.PULSE1: LEAD})}, 1.0) is None

    def test_a_held_bass_on_a_stem_of_its_own_moves_the_level_onto_the_triangle(
        self,
        config: Config,
        window: Window,
        all_channels: Dict[ChannelName, GeneratorUnion],
        joint_matcher: FrameMatcher,
    ) -> None:
        fitter = _fitter(TRIANGLE_ONLY, config, window, all_channels, joint_matcher)

        factor = fitter.factor({0: _held(config, {ChannelName.TRIANGLE: BASS})}, 1.0 / LEVEL)

        assert factor == pytest.approx(LEVEL, rel=LEVEL_TOLERANCE)

    def test_a_bass_in_short_notes_between_rests_on_a_stem_of_its_own_keeps_the_level(
        self,
        config: Config,
        window: Window,
        all_channels: Dict[ChannelName, GeneratorUnion],
        joint_matcher: FrameMatcher,
    ) -> None:
        fitter = _fitter(TRIANGLE_ONLY, config, window, all_channels, joint_matcher)

        assert fitter.factor({0: _detached(config)}, 1.0 / LEVEL) is None
