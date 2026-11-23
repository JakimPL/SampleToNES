from dataclasses import dataclass
from typing import Final, Sequence, Tuple

import pytest

from sampletones_core.constants.enums import ChannelName
from sampletones_core.instructions import InstructionUnion, PulseInstruction, TriangleInstruction
from sampletones_core.reconstructions.reconstructor.contribution import Contribution
from sampletones_core.reconstructions.reconstructor.level import Judgment
from sampletones_core.reconstructions.reconstructor.level.judgment import (
    BASS_DISTANCE,
    LEAST_CONFIRMED_SHARE,
    ChosenFrame,
)
from sampletones_core.reconstructions.reconstructor.matching import ScoredCandidate
from sampletones_core.reconstructions.reconstructor.stems.models.choice import StemChoice
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase

NOTE: Final[int] = 48
BINS: Final[int] = 4
SAMPLES: Final[int] = 8
COST: Final[float] = 0.3
CHEAPER: Final[float] = 0.1
SILENT_TRIANGLE: Final[TriangleInstruction] = TriangleInstruction(on=False, pitch=NOTE)
PULSE_ON_THE_BASS: Final[PulseInstruction] = PulseInstruction(on=True, pitch=NOTE, volume=15, duty_cycle=2)


def _choice(channel_name: ChannelName, instruction: InstructionUnion, cost: float) -> StemChoice:
    candidate = ScoredCandidate(instruction=instruction, cost=cost, contribution=Contribution.silence(BINS, SAMPLES))
    return StemChoice(stem_id=0, channel_name=channel_name, column=(candidate,))


def _triangle(pitch: int, cost: float = COST) -> StemChoice:
    return _choice(ChannelName.TRIANGLE, TriangleInstruction(on=True, pitch=pitch), cost)


def _frame(choices: Sequence[StemChoice]) -> ChosenFrame:
    return ChosenFrame(choices=tuple(choices), note=NOTE)


def _confirming(cost: float) -> ChosenFrame:
    return _frame([_triangle(NOTE, cost)])


def _refusing(cost: float) -> ChosenFrame:
    return _frame([_choice(ChannelName.PULSE1, PULSE_ON_THE_BASS, cost)])


SILENT_FRAME: Final[ChosenFrame] = ChosenFrame(choices=(), note=NOTE)


class TestWhetherAFrameConfirmsTheBass(BaseTestSuite):
    """A frame confirms the bass where a channel its stem holds plays the triangle near the note read."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        choices: Tuple[StemChoice, ...]
        expected: bool

    test_cases = (
        TestCase(label="the_triangle_on_the_note", choices=(_triangle(NOTE),), expected=True),
        TestCase(label="the_triangle_a_distance_above", choices=(_triangle(NOTE + BASS_DISTANCE),), expected=True),
        TestCase(label="the_triangle_a_distance_below", choices=(_triangle(NOTE - BASS_DISTANCE),), expected=True),
        TestCase(
            label="the_triangle_beyond_the_distance", choices=(_triangle(NOTE + BASS_DISTANCE + 1),), expected=False
        ),
        TestCase(
            label="the_triangle_silent", choices=(_choice(ChannelName.TRIANGLE, SILENT_TRIANGLE, COST),), expected=False
        ),
        TestCase(
            label="a_pulse_on_the_note", choices=(_choice(ChannelName.PULSE1, PULSE_ON_THE_BASS, COST),), expected=False
        ),
        TestCase(
            label="a_pulse_beside_the_triangle_on_the_note",
            choices=(_choice(ChannelName.PULSE1, PULSE_ON_THE_BASS, COST), _triangle(NOTE)),
            expected=True,
        ),
        TestCase(label="no_channel_held", choices=(), expected=False),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_a_frame_confirms_the_bass_on_the_triangle_alone(self, test_case: TestCase) -> None:
        assert _frame(test_case.choices).confirms is test_case.expected


class TestAChosenFramesCost:
    def test_a_frame_costs_its_cheapest_column_head(self) -> None:
        frame = _frame([_triangle(NOTE, COST), _choice(ChannelName.PULSE1, PULSE_ON_THE_BASS, CHEAPER)])

        assert frame.chosen
        assert frame.cost == CHEAPER

    def test_a_frame_its_stem_leaves_silent_has_no_cost(self) -> None:
        assert not SILENT_FRAME.chosen
        with pytest.raises(ValueError):
            _ = SILENT_FRAME.cost


class TestAJudgment:
    def test_the_cost_is_the_median_of_the_frames_chosen(self) -> None:
        frames = [_confirming(CHEAPER), _confirming(COST), _confirming(100.0)]

        assert Judgment.of(frames).cost == COST

    def test_a_frame_left_silent_counts_against_the_bass_and_outside_the_cost(self) -> None:
        judgment = Judgment.of([_confirming(COST), SILENT_FRAME])

        assert judgment.cost == COST
        assert judgment.confirmed == pytest.approx(0.5)

    def test_frames_all_left_silent_cost_without_bound(self) -> None:
        judgment = Judgment.of([SILENT_FRAME, SILENT_FRAME])

        assert judgment.cost == float("inf")
        assert judgment.confirmed == 0.0

    def test_the_confirmed_share_counts_the_frames_whose_triangle_plays_the_bass(self) -> None:
        frames = [_confirming(COST), _refusing(COST), _confirming(COST), _confirming(COST)]

        assert Judgment.of(frames).confirmed == pytest.approx(0.75)

    def test_an_empty_sample_confirms_nothing(self) -> None:
        judgment = Judgment.of([])

        assert judgment.cost == float("inf")
        assert judgment.confirmed == 0.0


class TestWhetherAMovedLevelHolds(BaseTestSuite):
    """A moved level holds where the triangle plays the bass on enough frames and the frames cost less."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        confirmed: float
        cost: float
        expected: bool

    test_cases = (
        TestCase(label="confirmed_and_cheaper", confirmed=1.0, cost=CHEAPER, expected=True),
        TestCase(label="exactly_the_share_confirmed", confirmed=LEAST_CONFIRMED_SHARE, cost=CHEAPER, expected=True),
        TestCase(
            label="under_the_share_confirmed", confirmed=LEAST_CONFIRMED_SHARE - 0.01, cost=CHEAPER, expected=False
        ),
        TestCase(label="costing_the_same", confirmed=1.0, cost=COST, expected=False),
        TestCase(label="costing_more", confirmed=1.0, cost=2 * COST, expected=False),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_a_moved_level_holds_where_the_choice_confirms_it_and_costs_less(self, test_case: TestCase) -> None:
        first = Judgment(cost=COST, confirmed=0.0)
        moved = Judgment(cost=test_case.cost, confirmed=test_case.confirmed)

        assert moved.holds_over(first) is test_case.expected

    def test_the_first_level_s_own_confirmation_has_no_say(self) -> None:
        moved = Judgment(cost=CHEAPER, confirmed=1.0)

        assert moved.holds_over(Judgment(cost=COST, confirmed=1.0))
        assert moved.holds_over(Judgment(cost=COST, confirmed=0.0))
