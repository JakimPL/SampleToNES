from dataclasses import dataclass
from typing import Dict, Final, List, Optional

import numpy as np
import pytest

from sampletones_core.configs import Config
from sampletones_core.constants.enums import ChannelName
from sampletones_core.fft import FragmentedAudio, Window
from sampletones_core.generators import GeneratorUnion, render_instructions
from sampletones_core.instructions import InstructionUnion, PulseInstruction, TriangleInstruction
from sampletones_core.reconstructions.reconstructor.level import Judgment, LevelFitter, LevelReading
from sampletones_core.reconstructions.reconstructor.level.fitted import JUDGED_FRAMES, SOUNDING_REACH
from sampletones_core.reconstructions.reconstructor.level.line import LEAST_STANDING_FRAMES
from sampletones_core.reconstructions.reconstructor.matching import FrameMatcher
from sampletones_core.reconstructions.reconstructor.stems.configs.config import StemsConfig
from sampletones_core.reconstructions.reconstructor.stems.configs.entry import StemEntry
from sampletones_core.reconstructions.reconstructor.stems.configs.hierarchy import StemsHierarchy
from sampletones_core.reconstructions.reconstructor.stems.configs.settings import StemSettings
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase

from ..conftest import rendered_audio

LEVEL: Final[float] = 0.6
QUIETER_LINE: Final[float] = 0.5
QUIET_BASS: Final[float] = 0.2
NOTE: Final[int] = 48
BASS: Final[TriangleInstruction] = TriangleInstruction(on=True, pitch=NOTE)
REST: Final[TriangleInstruction] = TriangleInstruction.null_instruction()
LEAD: Final[PulseInstruction] = PulseInstruction(on=True, pitch=64, volume=12, duty_cycle=2)
LOW_PULSE: Final[PulseInstruction] = PulseInstruction(on=True, pitch=48, volume=15, duty_cycle=2)
LEGATO_PITCHES: Final[List[int]] = [45, 48, 57, 60]
LEGATO_NOTE_FRAMES: Final[int] = 2
HELD_FRAMES: Final[int] = 32
DETACHED_NOTE_FRAMES: Final[int] = 3
REST_FRAMES: Final[int] = 3
PADDING_FRAMES: Final[int] = 4
LEVEL_TOLERANCE: Final[float] = 0.05
EVERY_CHANNEL: Final[List[ChannelName]] = ChannelName.items()
PULSES: Final[List[ChannelName]] = [ChannelName.PULSE1, ChannelName.PULSE2]
TRIANGLE_ONLY: Final[List[ChannelName]] = [ChannelName.TRIANGLE]
LEAD_STEM: Final[int] = 0
BASS_STEM: Final[int] = 1
QUIETER_STEM: Final[int] = 2
SHORTEST_LINE: Final[int] = 2 * SOUNDING_REACH + LEAST_STANDING_FRAMES


def _fitter(
    stems: StemsConfig,
    config: Config,
    window: Window,
    all_channels: Dict[ChannelName, GeneratorUnion],
    joint_matcher: FrameMatcher,
) -> LevelFitter:
    return LevelFitter(stems, all_channels, joint_matcher, config, window)


def _one_stem(channels: List[ChannelName]) -> StemsConfig:
    return StemsConfig.single_entry(StemSettings.covering(channels))


def _stems(channels: Dict[int, List[ChannelName]]) -> StemsConfig:
    """Stems on one precedence level, each covering its channels."""
    return StemsConfig(
        entries=tuple(
            StemEntry(id=stem_id, settings=StemSettings.covering(covered)) for stem_id, covered in channels.items()
        ),
        hierarchy=StemsHierarchy(levels=(tuple(channels),)),
    )


def _held(config: Config, notes: Dict[ChannelName, InstructionUnion]) -> np.ndarray:
    return rendered_audio(config, notes, HELD_FRAMES)


def _triangle_line(config: Config, line: List[TriangleInstruction]) -> np.ndarray:
    return render_instructions(line, ChannelName.TRIANGLE, config)


def _detached(config: Config) -> np.ndarray:
    """The bass played in short notes with rests between them, over as many frames as a held note."""
    period = [BASS] * DETACHED_NOTE_FRAMES + [REST] * REST_FRAMES
    return _triangle_line(config, (period * (HELD_FRAMES // len(period) + 1))[:HELD_FRAMES])


def _between_rests(config: Config, frames: int) -> np.ndarray:
    """The bass held ``frames`` frames, with rests before and after it."""
    return _triangle_line(config, [REST] * PADDING_FRAMES + [BASS] * frames + [REST] * PADDING_FRAMES)


def _legato(config: Config) -> np.ndarray:
    """A line changing note every ``LEGATO_NOTE_FRAMES`` frames, each change within a low note's window."""
    line = [TriangleInstruction(on=True, pitch=pitch) for pitch in LEGATO_PITCHES for _ in range(LEGATO_NOTE_FRAMES)]
    return _triangle_line(config, (line * (HELD_FRAMES // len(line) + 1))[:HELD_FRAMES])


def _framed(config: Config, window: Window, recording: np.ndarray, coefficient: float) -> FragmentedAudio:
    return FragmentedAudio.create(recording / coefficient, config, window)


@dataclass(frozen=True)
class FittedBass:
    """Every step of fitting the level of a held bass under a lead, played at ``LEVEL`` of the triangle's."""

    frames: FragmentedAudio
    reading: LevelReading
    first: Judgment
    moved: Judgment
    factor: Optional[float]


@pytest.fixture(name="fitted_bass", scope="class")
def fitted_bass_fixture(
    config: Config, window: Window, all_channels: Dict[ChannelName, GeneratorUnion], joint_matcher: FrameMatcher
) -> FittedBass:
    fitter = _fitter(_one_stem(EVERY_CHANNEL), config, window, all_channels, joint_matcher)
    recording = _held(config, {ChannelName.TRIANGLE: BASS, ChannelName.PULSE1: LEAD})
    coefficient = 1.0 / LEVEL
    frames = _framed(config, window, recording, coefficient)
    reading = fitter.read({0: frames})
    assert reading.level is not None
    sample = reading.sample(JUDGED_FRAMES)
    return FittedBass(
        frames=frames,
        reading=reading,
        first=fitter.judged(sample, {0: frames}),
        moved=fitter.judged(sample, {0: _framed(config, window, recording, coefficient * reading.level)}),
        factor=fitter.factor({0: recording}, coefficient),
    )


class TestFittingTheLevelOfAHeldBassUnderALead:
    def test_every_frame_the_recording_sounds_through_is_read_from_the_first_to_the_last(
        self, fitted_bass: FittedBass
    ) -> None:
        frames = len(fitted_bass.frames)

        assert fitted_bass.reading.sampled == frames - 2 * SOUNDING_REACH
        assert [frame.index for frame in fitted_bass.reading.standing] == list(
            range(SOUNDING_REACH, frames - SOUNDING_REACH)
        )

    def test_every_frame_read_stands_on_the_bass(self, fitted_bass: FittedBass) -> None:
        assert {frame.reading.note for frame in fitted_bass.reading.standing} == {NOTE}

    def test_the_frames_agree_on_the_level_the_bass_plays_at(self, fitted_bass: FittedBass) -> None:
        assert fitted_bass.reading.level == pytest.approx(LEVEL, rel=LEVEL_TOLERANCE)

    def test_at_the_level_read_the_triangle_plays_the_bass_and_the_frames_cost_less(
        self, fitted_bass: FittedBass
    ) -> None:
        assert fitted_bass.moved.confirmed == 1.0
        assert fitted_bass.moved.cost < fitted_bass.first.cost

    def test_the_working_level_moves_by_the_level_read(self, fitted_bass: FittedBass) -> None:
        assert fitted_bass.factor == fitted_bass.reading.level


class TestALevelAtAnyStart(BaseTestSuite):
    """The level a held bass stands at reads alike wherever within a frame the recording starts."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        offset: float

    test_cases = (
        TestCase(label="at_a_frame_s_start", offset=0.0),
        TestCase(label="a_quarter_frame_late", offset=0.25),
        TestCase(label="half_a_frame_late", offset=0.5),
        TestCase(label="three_quarters_of_a_frame_late", offset=0.75),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_a_bass_started_within_a_frame_moves_the_level_onto_the_triangle(
        self,
        config: Config,
        window: Window,
        all_channels: Dict[ChannelName, GeneratorUnion],
        joint_matcher: FrameMatcher,
        test_case: TestCase,
    ) -> None:
        fitter = _fitter(_one_stem(TRIANGLE_ONLY), config, window, all_channels, joint_matcher)
        bass = _held(config, {ChannelName.TRIANGLE: BASS})
        late = np.concatenate([np.zeros(int(test_case.offset * config.library.frame_length), dtype=bass.dtype), bass])

        factor = fitter.factor({0: late}, 1.0 / LEVEL)

        assert factor == pytest.approx(LEVEL, rel=LEVEL_TOLERANCE)


class TestWhereTheLevelStays:
    def test_a_low_pulse_a_triangle_would_only_stand_in_for_keeps_the_level(
        self,
        config: Config,
        window: Window,
        all_channels: Dict[ChannelName, GeneratorUnion],
        joint_matcher: FrameMatcher,
    ) -> None:
        fitter = _fitter(_one_stem(EVERY_CHANNEL), config, window, all_channels, joint_matcher)

        assert fitter.factor({0: _held(config, {ChannelName.PULSE1: LOW_PULSE})}, 1.0) is None

    def test_a_setup_without_the_triangle_keeps_the_level(
        self,
        config: Config,
        window: Window,
        all_channels: Dict[ChannelName, GeneratorUnion],
        joint_matcher: FrameMatcher,
    ) -> None:
        fitter = _fitter(_one_stem(PULSES), config, window, all_channels, joint_matcher)

        assert not fitter.entries
        assert fitter.factor({0: _held(config, {ChannelName.PULSE1: LEAD})}, 1.0) is None

    def test_a_lead_alone_holds_no_triangle_line_and_keeps_the_level(
        self,
        config: Config,
        window: Window,
        all_channels: Dict[ChannelName, GeneratorUnion],
        joint_matcher: FrameMatcher,
    ) -> None:
        fitter = _fitter(_one_stem(EVERY_CHANNEL), config, window, all_channels, joint_matcher)
        lead = _held(config, {ChannelName.PULSE1: LEAD})

        assert not fitter.read({0: _framed(config, window, lead, 1.0)}).standing
        assert fitter.factor({0: lead}, 1.0) is None

    def test_a_silent_recording_reads_no_frame_and_keeps_the_level(
        self,
        config: Config,
        window: Window,
        all_channels: Dict[ChannelName, GeneratorUnion],
        joint_matcher: FrameMatcher,
    ) -> None:
        fitter = _fitter(_one_stem(EVERY_CHANNEL), config, window, all_channels, joint_matcher)
        silence = np.zeros(HELD_FRAMES * config.library.frame_length, dtype=np.float32)

        assert fitter.read({0: _framed(config, window, silence, 1.0)}).sampled == 0
        assert fitter.factor({0: silence}, 1.0) is None

    def test_a_bass_too_quiet_under_a_lead_to_hold_the_frame_keeps_the_level(
        self,
        config: Config,
        window: Window,
        all_channels: Dict[ChannelName, GeneratorUnion],
        joint_matcher: FrameMatcher,
    ) -> None:
        fitter = _fitter(_one_stem(EVERY_CHANNEL), config, window, all_channels, joint_matcher)
        quiet = _held(config, {ChannelName.TRIANGLE: BASS}) * QUIET_BASS + _held(config, {ChannelName.PULSE1: LEAD})

        reading = fitter.read({0: _framed(config, window, quiet, 1.0)})

        assert reading.sampled == HELD_FRAMES - 2 * SOUNDING_REACH
        assert not reading.standing
        assert fitter.factor({0: quiet}, 1.0) is None

    def test_a_bass_in_short_notes_between_rests_on_a_stem_of_its_own_keeps_the_level(
        self,
        config: Config,
        window: Window,
        all_channels: Dict[ChannelName, GeneratorUnion],
        joint_matcher: FrameMatcher,
    ) -> None:
        fitter = _fitter(_one_stem(TRIANGLE_ONLY), config, window, all_channels, joint_matcher)

        assert fitter.read({0: _framed(config, window, _detached(config), 1.0 / LEVEL)}).sampled == 0
        assert fitter.factor({0: _detached(config)}, 1.0 / LEVEL) is None

    def test_a_line_changing_note_within_the_window_reads_quieter_and_the_choice_refuses_it(
        self,
        config: Config,
        window: Window,
        all_channels: Dict[ChannelName, GeneratorUnion],
        joint_matcher: FrameMatcher,
    ) -> None:
        fitter = _fitter(_one_stem(TRIANGLE_ONLY), config, window, all_channels, joint_matcher)
        legato = _legato(config)

        level = fitter.read({0: _framed(config, window, legato, 1.0 / LEVEL)}).level

        assert level is not None and level < LEVEL * (1.0 - LEVEL_TOLERANCE)
        assert fitter.factor({0: legato}, 1.0 / LEVEL) is None

    def test_a_level_already_on_the_triangle_line_stays_where_the_level_read_costs_no_less(
        self,
        config: Config,
        window: Window,
        all_channels: Dict[ChannelName, GeneratorUnion],
        joint_matcher: FrameMatcher,
    ) -> None:
        fitter = _fitter(_one_stem(EVERY_CHANNEL), config, window, all_channels, joint_matcher)
        recording = _held(config, {ChannelName.TRIANGLE: BASS, ChannelName.PULSE1: LEAD})

        assert fitter.read({0: _framed(config, window, recording, 1.0)}).level == pytest.approx(
            1.0, rel=LEVEL_TOLERANCE
        )
        assert fitter.factor({0: recording}, 1.0) is None


class TestTheShortestLine(BaseTestSuite):
    """A line stands on as few frames as it may, each sounded through on either side."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        frames: int
        expected: bool

    test_cases = (
        TestCase(label="held_just_long_enough", frames=SHORTEST_LINE, expected=True),
        TestCase(label="held_a_frame_too_short", frames=SHORTEST_LINE - 1, expected=False),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_a_bass_between_rests_stands_once_enough_of_its_frames_sound_through(
        self,
        config: Config,
        window: Window,
        all_channels: Dict[ChannelName, GeneratorUnion],
        joint_matcher: FrameMatcher,
        test_case: TestCase,
    ) -> None:
        fitter = _fitter(_one_stem(TRIANGLE_ONLY), config, window, all_channels, joint_matcher)
        recording = _between_rests(config, test_case.frames)

        reading = fitter.read({0: _framed(config, window, recording, 1.0 / LEVEL)})

        assert reading.sampled == test_case.frames - 2 * SOUNDING_REACH
        assert (reading.level is not None) is test_case.expected
        assert (fitter.factor({0: recording}, 1.0 / LEVEL) is not None) is test_case.expected


class TestFittingTheLevelOfSeveralStems:
    def test_a_bass_on_a_stem_of_its_own_moves_the_level_and_the_lead_s_stem_is_left_unread(
        self,
        config: Config,
        window: Window,
        all_channels: Dict[ChannelName, GeneratorUnion],
        joint_matcher: FrameMatcher,
    ) -> None:
        fitter = _fitter(
            _stems({LEAD_STEM: PULSES, BASS_STEM: TRIANGLE_ONLY}), config, window, all_channels, joint_matcher
        )
        recordings = {
            LEAD_STEM: _held(config, {ChannelName.PULSE1: LEAD}),
            BASS_STEM: _held(config, {ChannelName.TRIANGLE: BASS}),
        }

        reading = fitter.read({BASS_STEM: _framed(config, window, recordings[BASS_STEM], 1.0 / LEVEL)})

        assert [entry.id for entry in fitter.entries] == [BASS_STEM]
        assert {frame.stem_id for frame in reading.standing} == {BASS_STEM}
        assert fitter.factor(recordings, 1.0 / LEVEL) == pytest.approx(LEVEL, rel=LEVEL_TOLERANCE)

    def test_two_stems_sounding_the_triangle_are_read_together_and_lines_at_two_levels_disagree(
        self,
        config: Config,
        window: Window,
        all_channels: Dict[ChannelName, GeneratorUnion],
        joint_matcher: FrameMatcher,
    ) -> None:
        stems = _stems({BASS_STEM: TRIANGLE_ONLY, QUIETER_STEM: TRIANGLE_ONLY})
        fitter = _fitter(stems, config, window, all_channels, joint_matcher)
        bass = _held(config, {ChannelName.TRIANGLE: BASS})
        recordings = {BASS_STEM: bass, QUIETER_STEM: bass * QUIETER_LINE}
        frames = {stem_id: _framed(config, window, recording, 1.0 / LEVEL) for stem_id, recording in recordings.items()}

        reading = fitter.read(frames)

        read = HELD_FRAMES - 2 * SOUNDING_REACH
        assert reading.sampled == 2 * read
        assert [frame.stem_id for frame in reading.standing] == [BASS_STEM] * read + [QUIETER_STEM] * read
        assert reading.stands and not reading.agrees
        assert fitter.factor(recordings, 1.0 / LEVEL) is None
