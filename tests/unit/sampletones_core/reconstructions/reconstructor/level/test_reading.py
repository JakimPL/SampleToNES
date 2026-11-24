from dataclasses import dataclass
from typing import Dict, Final, List, Mapping, Sequence, Tuple

import numpy as np
import pytest

from sampletones_core.configs import Config
from sampletones_core.constants.enums import ChannelName, GeneratorClassName
from sampletones_core.fft import Fragment
from sampletones_core.fft.features import FeatureExtractor
from sampletones_core.generators import GeneratorUnion
from sampletones_core.instructions import InstructionUnion, PulseInstruction, TriangleInstruction
from sampletones_core.reconstructions.reconstructor.level import FrameReading, TriangleReader
from sampletones_core.reconstructions.reconstructor.level.reading import (
    FREE_TRIANGLE_REACH,
    RUN_SHARE,
    RUN_STEP,
    STANDING_SHARE,
    TriangleNote,
    TriangleRun,
)
from sampletones_core.reconstructions.reconstructor.matching import FrameMatcher
from sampletones_core.reconstructions.reconstructor.stems.assignment.joint.catalog import KindCatalog
from sampletones_core.reconstructions.reconstructor.stems.assignment.joint.layout import StemLayout
from sampletones_core.reconstructions.reconstructor.stems.configs.config import StemsConfig
from sampletones_core.reconstructions.reconstructor.stems.configs.settings import StemSettings
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase

from ..conftest import JOINT_TRIANGLE_PITCHES, rendered_audio

BASS: Final[TriangleInstruction] = TriangleInstruction(on=True, pitch=48)
LEAD: Final[PulseInstruction] = PulseInstruction(on=True, pitch=64, volume=12, duty_cycle=2)
HALF: Final[float] = 0.5
FULL: Final[float] = 1.0
DRIVE: Final[float] = 2.0
LEVEL_TOLERANCE: Final[float] = 0.05
HELD_FRAMES: Final[int] = 48
EVERY_CHANNEL: Final[List[ChannelName]] = ChannelName.items()
PULSES: Final[List[ChannelName]] = [ChannelName.PULSE1, ChannelName.PULSE2]
NOTE: Final[int] = 48
TOTAL: Final[float] = 1.0
NATURAL: Final[float] = 0.25


def _frame(
    config: Config, extractor: FeatureExtractor, notes: Mapping[ChannelName, InstructionUnion], scale: float
) -> Fragment:
    """A frame from the middle of ``notes`` held together, played at ``scale`` of the level they render at.

    The notes are held long enough for the window of the lowest bin a frame reads to lie within them.
    """
    return extractor.extract(rendered_audio(config, notes, HELD_FRAMES) * scale)[HELD_FRAMES // 2]


def _reader(stems: StemsConfig, channels: Dict[ChannelName, GeneratorUnion], matcher: FrameMatcher) -> TriangleReader:
    layout = StemLayout.of(stems.entries[0], channels)
    catalogs: Dict[GeneratorClassName, KindCatalog] = {
        slot.kind: KindCatalog.build(matcher.candidate_provider, channels[slot.channel_name]) for slot in layout.slots
    }
    return TriangleReader.of(layout, catalogs, matcher)


def _read(reader: TriangleReader, fragment: Fragment) -> FrameReading:
    reading = reader.read(fragment)
    assert reading is not None
    return reading


def _notes(strengths: Mapping[int, float]) -> List[TriangleNote]:
    """Triangle notes, ascending, each at a level of a tenth of its strength."""
    return [
        TriangleNote(note=note, level=strength / 10, strength=strength) for note, strength in sorted(strengths.items())
    ]


def _run_notes(runs: Sequence[TriangleRun]) -> List[Tuple[int, ...]]:
    return [tuple(note.note for note in run.notes) for run in runs]


@pytest.fixture(name="reader")
def reader_fixture(all_channels: Dict[ChannelName, GeneratorUnion], joint_matcher: FrameMatcher) -> TriangleReader:
    return _reader(StemsConfig.single_entry(StemSettings.covering(EVERY_CHANNEL)), all_channels, joint_matcher)


class TestTheTriangleReader:
    def test_a_bass_on_the_triangle_reads_the_level_it_plays_at(
        self, config: Config, extractor: FeatureExtractor, reader: TriangleReader
    ) -> None:
        reading = _read(reader, _frame(config, extractor, {ChannelName.TRIANGLE: BASS}, HALF))

        assert reading.level == pytest.approx(HALF, rel=LEVEL_TOLERANCE)
        assert reading.note == BASS.pitch

    def test_a_bass_louder_than_the_triangle_plays_reads_its_own_level(
        self, config: Config, extractor: FeatureExtractor, reader: TriangleReader
    ) -> None:
        louder = np.sqrt(FREE_TRIANGLE_REACH) / 2

        reading = _read(reader, _frame(config, extractor, {ChannelName.TRIANGLE: BASS}, louder))

        assert reading.level == pytest.approx(louder, rel=LEVEL_TOLERANCE)

    def test_a_bass_under_a_lead_reads_its_own_level(
        self, config: Config, extractor: FeatureExtractor, reader: TriangleReader
    ) -> None:
        notes = {ChannelName.TRIANGLE: BASS, ChannelName.PULSE1: LEAD}

        reading = _read(reader, _frame(config, extractor, notes, FULL))

        assert reading.level == pytest.approx(FULL, rel=LEVEL_TOLERANCE)
        assert reading.note == BASS.pitch

    @pytest.mark.parametrize(
        "pitch", [min(JOINT_TRIANGLE_PITCHES), max(JOINT_TRIANGLE_PITCHES)], ids=["lowest", "highest"]
    )
    def test_a_bass_at_either_end_of_the_triangle_s_notes_reads_its_level(
        self, config: Config, extractor: FeatureExtractor, reader: TriangleReader, pitch: int
    ) -> None:
        bass = TriangleInstruction(on=True, pitch=pitch)

        reading = _read(reader, _frame(config, extractor, {ChannelName.TRIANGLE: bass}, HALF))

        assert reading.level == pytest.approx(HALF, rel=LEVEL_TOLERANCE)
        assert reading.note == pitch

    def test_a_lead_alone_holds_no_triangle_line(
        self, config: Config, extractor: FeatureExtractor, reader: TriangleReader
    ) -> None:
        assert reader.read(_frame(config, extractor, {ChannelName.PULSE1: LEAD}, FULL)) is None

    def test_a_stem_driving_the_triangle_harder_reads_against_the_level_it_plays_it_at(
        self,
        config: Config,
        extractor: FeatureExtractor,
        all_channels: Dict[ChannelName, GeneratorUnion],
        joint_matcher: FrameMatcher,
    ) -> None:
        settings = StemSettings.covering(EVERY_CHANNEL).with_drive(ChannelName.TRIANGLE, DRIVE)
        reader = _reader(StemsConfig.single_entry(settings), all_channels, joint_matcher)

        reading = _read(reader, _frame(config, extractor, {ChannelName.TRIANGLE: BASS}, FULL / DRIVE))

        assert reader.atoms.caps[reader.triangle] == pytest.approx(reader.natural)
        assert reading.level == pytest.approx(FULL, rel=LEVEL_TOLERANCE)

    def test_a_stem_without_the_triangle_has_no_level_to_read(
        self, all_channels: Dict[ChannelName, GeneratorUnion], joint_matcher: FrameMatcher
    ) -> None:
        with pytest.raises(ValueError):
            _reader(StemsConfig.single_entry(StemSettings.covering(PULSES)), all_channels, joint_matcher)


class TestTheRunsOfTriangleNotes:
    def test_notes_a_step_apart_join_one_run_and_farther_notes_start_another(self) -> None:
        notes = _notes({NOTE: 1.0, NOTE + RUN_STEP: 1.0, NOTE + 2 * RUN_STEP + 1: 1.0})

        assert _run_notes(TriangleRun.split(notes)) == [(NOTE, NOTE + RUN_STEP), (NOTE + 2 * RUN_STEP + 1,)]

    def test_no_note_makes_no_run(self) -> None:
        assert TriangleRun.split([]) == []

    def test_a_run_sounds_its_notes_together(self) -> None:
        (run,) = TriangleRun.split(_notes({NOTE: 0.2, NOTE + RUN_STEP: 0.3}))

        assert run.strength == pytest.approx(0.5)
        assert run.level == pytest.approx(0.05)

    def test_a_run_is_centered_on_its_strongest_note(self) -> None:
        (run,) = TriangleRun.split(_notes({NOTE: 0.2, NOTE + RUN_STEP: 0.3}))

        assert run.center == NOTE + RUN_STEP

    def test_of_notes_equally_strong_the_lower_centers_the_run(self) -> None:
        (run,) = TriangleRun.split(_notes({NOTE: 0.3, NOTE + RUN_STEP: 0.3}))

        assert run.center == NOTE

    def test_a_run_reads_the_square_root_of_its_level_against_the_triangle_s(self) -> None:
        (run,) = TriangleRun.split(_notes({NOTE: 0.2, NOTE + RUN_STEP: 0.3}))

        reading = run.reading(NATURAL)

        assert reading.level == pytest.approx(np.sqrt(run.level / NATURAL))
        assert reading.note == run.center


class TestTheBassOfAFrame(BaseTestSuite):
    """The bass is the lowest run of notes holding their share each that holds the standing share together."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        strengths: Dict[int, float]
        expected: Tuple[int, ...]

    test_cases = (
        TestCase(
            label="the_lowest_standing_run_over_a_stronger_one_above",
            strengths={NOTE: STANDING_SHARE * TOTAL, NOTE + 12: 0.6 * TOTAL},
            expected=(NOTE,),
        ),
        TestCase(
            label="a_run_short_of_the_standing_share_leaves_the_bass_to_the_run_above",
            strengths={NOTE: 0.9 * STANDING_SHARE * TOTAL, NOTE + 12: STANDING_SHARE * TOTAL},
            expected=(NOTE + 12,),
        ),
        TestCase(
            label="neighbors_standing_together_though_neither_alone",
            strengths={NOTE: 0.6 * STANDING_SHARE * TOTAL, NOTE + RUN_STEP: 0.6 * STANDING_SHARE * TOTAL},
            expected=(NOTE, NOTE + RUN_STEP),
        ),
        TestCase(
            label="a_note_under_the_run_share_splits_its_neighbors",
            strengths={
                NOTE: 0.6 * STANDING_SHARE * TOTAL,
                NOTE + RUN_STEP: 0.5 * RUN_SHARE * TOTAL,
                NOTE + 2 * RUN_STEP: 0.6 * STANDING_SHARE * TOTAL,
            },
            expected=(),
        ),
        TestCase(
            label="a_note_exactly_at_the_run_share_joins_its_neighbors",
            strengths={
                NOTE: 0.6 * STANDING_SHARE * TOTAL,
                NOTE + RUN_STEP: RUN_SHARE * TOTAL,
                NOTE + 2 * RUN_STEP: 0.6 * STANDING_SHARE * TOTAL,
            },
            expected=(NOTE, NOTE + RUN_STEP, NOTE + 2 * RUN_STEP),
        ),
        TestCase(
            label="a_note_under_the_run_share_adds_nothing_to_a_run",
            strengths={NOTE: 0.9 * RUN_SHARE * TOTAL, NOTE + RUN_STEP: 0.99 * STANDING_SHARE * TOTAL},
            expected=(),
        ),
        TestCase(label="no_triangle_note_sounding", strengths={}, expected=()),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_bass_is_the_lowest_run_holding_the_standing_share(self, test_case: TestCase) -> None:
        bass = TriangleRun.bass(_notes(test_case.strengths), TOTAL)

        assert (() if bass is None else tuple(note.note for note in bass.notes)) == test_case.expected
