from dataclasses import dataclass
from typing import Dict, Final, List, Sequence, Set, Tuple

import pytest

from sampletones_player.specification.screen import TILE_SIDE
from sampletones_tools.player.graphics.deck.groups import (
    OTHER_METER_GROUP,
    PROGRESS_GROUP,
    PULSE_METER_GROUP,
)
from sampletones_tools.player.graphics.deck.meters import (
    METER_PAIRS,
    METER_STEPS_PER_TILE,
    PROGRESS_STEPS,
    meter_members,
    progress_members,
)
from sampletones_tools.player.graphics.deck.state import MAX_LEVEL
from sampletones_tools.player.graphics.sheet.drawing import Pixels
from sampletones_tools.player.graphics.sheet.groups import PatternTable
from sampletones_tools.player.graphics.sheet.sheet import TileSheet
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase

METER_TILES: Final[int] = 8
LAST_TILE_STEPS: Final[int] = MAX_LEVEL - METER_PAIRS * METER_STEPS_PER_TILE
TILE_STEPS: Final[Tuple[int, ...]] = (*[METER_STEPS_PER_TILE] * METER_PAIRS, LAST_TILE_STEPS)
LIT_STEPS: Final[Dict[str, int]] = {
    "meter_none": 0,
    "meter_first": 1,
    "meter_both": 2,
    "meter_last_dim": 0,
    "meter_last_lit": 1,
}
BRIGHTENING: Final[Tuple[Tuple[str, str], ...]] = (
    ("meter_none", "meter_first"),
    ("meter_first", "meter_both"),
    ("meter_last_dim", "meter_last_lit"),
)
FILLED_PIXELS: Final[Dict[str, int]] = {f"progress_{pixels}": pixels for pixels in range(PROGRESS_STEPS + 1)}
BAR_CELLS: Final[int] = 4
BAR_PIXELS: Final[int] = BAR_CELLS * TILE_SIDE
WIDE_BAR_CELLS: Final[int] = 28


@dataclass(frozen=True, kw_only=True)
class LevelCase(BaseRegularTestCase):
    level: int


@dataclass(frozen=True, kw_only=True)
class MeterGroupCase(BaseRegularTestCase):
    group: str


LEVEL_CASES: Final[Tuple[LevelCase, ...]] = tuple(
    LevelCase(level=level, label=f"level {level}") for level in range(MAX_LEVEL + 1)
)
METER_GROUP_CASES: Final[Tuple[MeterGroupCase, ...]] = (
    MeterGroupCase(group=PULSE_METER_GROUP, label="the pulse meters"),
    MeterGroupCase(group=OTHER_METER_GROUP, label="the other meters"),
)


def lit_steps(members: Sequence[str]) -> List[int]:
    return [LIT_STEPS[member] for member in members]


def filled_pixels(members: Sequence[str]) -> List[int]:
    return [FILLED_PIXELS[member] for member in members]


def fills_from_the_left(filled: Sequence[int], capacities: Sequence[int]) -> bool:
    """Whether a tile holds anything only once every tile left of it is full."""
    return all(filled[tile - 1] == capacities[tile - 1] for tile in range(1, len(filled)) if filled[tile] > 0)


def drawn(sheet: TileSheet, group: str, member: str) -> Pixels:
    return sheet.drawn(PatternTable.BACKGROUND)[sheet.tile(PatternTable.BACKGROUND, group, member)]


def inked(sheet: TileSheet, group: str, member: str) -> Set[Tuple[int, int]]:
    """The pixels a group draws a member's ink at."""
    ink = sheet.table(PatternTable.BACKGROUND)[group].ink
    pixels = drawn(sheet, group, member)
    return {(row, column) for row in range(TILE_SIDE) for column in range(TILE_SIDE) if pixels[row][column] == ink}


def differing_columns(first: Pixels, second: Pixels) -> Set[int]:
    return {
        column for row in range(TILE_SIDE) for column in range(TILE_SIDE) if first[row][column] != second[row][column]
    }


class TestTheTilesOfALevelMeter(BaseTestSuite):
    test_cases = LEVEL_CASES

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_meter_is_eight_tiles_wide(self, test_case: LevelCase) -> None:
        assert len(meter_members(test_case.level)) == METER_TILES

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_lit_steps_count_back_to_the_level(self, test_case: LevelCase) -> None:
        assert sum(lit_steps(meter_members(test_case.level))) == test_case.level

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_meter_lights_from_the_left(self, test_case: LevelCase) -> None:
        assert fills_from_the_left(lit_steps(meter_members(test_case.level)), TILE_STEPS)

    def test_the_last_tile_holds_the_fifteenth_step_alone(self) -> None:
        assert lit_steps(meter_members(MAX_LEVEL - 1))[-1] == 0
        assert lit_steps(meter_members(MAX_LEVEL))[-1] == LAST_TILE_STEPS


class TestTheMetersOnTheShippedSheet(BaseTestSuite):
    test_cases = METER_GROUP_CASES

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_group_draws_every_tile_a_level_shows(
        self, test_case: MeterGroupCase, shipped_sheet: TileSheet
    ) -> None:
        shown = {member for level in range(MAX_LEVEL + 1) for member in meter_members(level)}

        assert shown <= set(shipped_sheet.table(PatternTable.BACKGROUND)[test_case.group].members)

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_lighting_a_step_adds_ink_and_takes_none_away(
        self,
        test_case: MeterGroupCase,
        shipped_sheet: TileSheet,
    ) -> None:
        for dimmer, brighter in BRIGHTENING:
            assert inked(shipped_sheet, test_case.group, dimmer) < inked(shipped_sheet, test_case.group, brighter)


class TestTheTilesOfAProgressBar(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        filled: int
        width: int

    test_cases = (
        TestCase(filled=0, width=BAR_CELLS, label="an empty bar"),
        TestCase(filled=1, width=BAR_CELLS, label="one pixel"),
        TestCase(filled=TILE_SIDE, width=BAR_CELLS, label="exactly the first tile"),
        TestCase(filled=TILE_SIDE + 1, width=BAR_CELLS, label="a pixel into the second tile"),
        TestCase(filled=BAR_PIXELS // 2 + 3, width=BAR_CELLS, label="past the middle"),
        TestCase(filled=BAR_PIXELS - 1, width=BAR_CELLS, label="a pixel short of full"),
        TestCase(filled=BAR_PIXELS, width=BAR_CELLS, label="a full bar"),
        TestCase(filled=BAR_PIXELS + TILE_SIDE, width=BAR_CELLS, label="more than the bar holds"),
        TestCase(filled=TILE_SIDE // 2, width=1, label="a bar of one tile"),
        TestCase(filled=WIDE_BAR_CELLS * TILE_SIDE // 3, width=WIDE_BAR_CELLS, label="a wide bar"),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_bar_is_a_tile_per_cell(self, test_case: TestCase) -> None:
        assert len(progress_members(test_case.filled, test_case.width)) == test_case.width

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_filled_pixels_sum_to_the_progress_the_bar_can_hold(self, test_case: TestCase) -> None:
        members = progress_members(test_case.filled, test_case.width)

        assert sum(filled_pixels(members)) == min(test_case.filled, test_case.width * TILE_SIDE)

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_bar_fills_from_the_left(self, test_case: TestCase) -> None:
        members = progress_members(test_case.filled, test_case.width)

        assert fills_from_the_left(filled_pixels(members), [PROGRESS_STEPS] * test_case.width)


class TestTheProgressBarOnTheShippedSheet(BaseTestSuite):
    def test_the_group_draws_every_step_a_tile_shows(self, shipped_sheet: TileSheet) -> None:
        assert set(FILLED_PIXELS) <= set(shipped_sheet.table(PatternTable.BACKGROUND)[PROGRESS_GROUP].members)

    def test_every_step_fills_the_next_column_of_pixels(self, shipped_sheet: TileSheet) -> None:
        for step in range(PROGRESS_STEPS):
            before = drawn(shipped_sheet, PROGRESS_GROUP, f"progress_{step}")
            after = drawn(shipped_sheet, PROGRESS_GROUP, f"progress_{step + 1}")

            assert differing_columns(before, after) == {step}
