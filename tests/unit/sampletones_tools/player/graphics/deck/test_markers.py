from dataclasses import dataclass
from typing import Final, Tuple

import pytest

from sampletones_player.specification.screen import PALETTES_PER_LAYER, TILE_SIDE
from sampletones_tools.player.graphics.deck.markers import (
    PIN_STEM_COLUMN,
    PIXELS_PER_PITCH,
    PULSE1_PIN,
    PULSE2_PIN,
    TRIANGLE_PIN,
    Pin,
)
from sampletones_tools.player.graphics.sheet.drawing import Pixels
from sampletones_tools.player.graphics.sheet.groups import PatternTable
from sampletones_tools.player.graphics.sheet.sheet import TileSheet
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase

PINS: Final[Tuple[Pin, ...]] = (PULSE1_PIN, PULSE2_PIN, TRIANGLE_PIN)
FOOT_ROW: Final[int] = TILE_SIDE - 1


def drawn(sheet: TileSheet, pin: Pin) -> Pixels:
    return sheet.drawn(PatternTable.SPRITES)[sheet.tile(PatternTable.SPRITES, pin.group, pin.member)]


class TestThePinOfAChannel(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        pin: Pin

    test_cases = (
        TestCase(pin=PULSE1_PIN, label="the first pulse"),
        TestCase(pin=PULSE2_PIN, label="the second pulse"),
        TestCase(pin=TRIANGLE_PIN, label="the triangle"),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_shipped_sprite_table_draws_it(self, test_case: TestCase, shipped_sheet: TileSheet) -> None:
        group = shipped_sheet.table(PatternTable.SPRITES)[test_case.pin.group]

        assert test_case.pin.member in group.members

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_it_takes_one_of_the_sprite_palettes(self, test_case: TestCase) -> None:
        assert test_case.pin.palette in range(PALETTES_PER_LAYER)

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_its_foot_covers_the_pixels_of_one_pitch_from_the_stem_column_on(
        self,
        test_case: TestCase,
        shipped_sheet: TileSheet,
    ) -> None:
        """A marker is placed by its stem, so the foot of the pin stands on the pixels its pitch takes."""
        foot = drawn(shipped_sheet, test_case.pin)[FOOT_ROW]

        standing = {column for column, entry in enumerate(foot) if entry}

        assert standing == set(range(PIN_STEM_COLUMN, PIN_STEM_COLUMN + PIXELS_PER_PITCH))


class TestThePinsTogether(BaseTestSuite):
    def test_every_channel_shows_a_pin_told_from_the_others(self, shipped_sheet: TileSheet) -> None:
        looks = {(drawn(shipped_sheet, pin), pin.palette) for pin in PINS}

        assert len(looks) == len(PINS)
