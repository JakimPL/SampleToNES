from dataclasses import dataclass

import pytest

from sampletones_tools.player.graphics.deck.groups import (
    BAR_GROUP,
    CHROME_GROUP,
    FIRST_PIN_GROUP,
    OTHER_METER_GROUP,
    OTHER_WAVE_GROUP,
    PROGRESS_GROUP,
    PULSE_METER_GROUP,
    PULSE_WAVE_GROUP,
    SECOND_PIN_GROUP,
)
from sampletones_tools.player.graphics.sheet.groups import PatternTable
from sampletones_tools.player.graphics.sheet.sheet import TileSheet
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase


class TestTheGroupsTheDeckDrawsFrom(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        table: PatternTable
        group: str

    test_cases = (
        TestCase(table=PatternTable.BACKGROUND, group=BAR_GROUP, label="the bar"),
        TestCase(table=PatternTable.BACKGROUND, group=CHROME_GROUP, label="the chrome"),
        TestCase(table=PatternTable.BACKGROUND, group=PROGRESS_GROUP, label="the progress bar"),
        TestCase(table=PatternTable.BACKGROUND, group=PULSE_WAVE_GROUP, label="the pulse waves"),
        TestCase(table=PatternTable.BACKGROUND, group=OTHER_WAVE_GROUP, label="the other waves"),
        TestCase(table=PatternTable.BACKGROUND, group=PULSE_METER_GROUP, label="the pulse meters"),
        TestCase(table=PatternTable.BACKGROUND, group=OTHER_METER_GROUP, label="the other meters"),
        TestCase(table=PatternTable.SPRITES, group=FIRST_PIN_GROUP, label="the first pins"),
        TestCase(table=PatternTable.SPRITES, group=SECOND_PIN_GROUP, label="the second pins"),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_shipped_sheet_holds_the_group_in_its_table(
        self,
        test_case: TestCase,
        shipped_sheet: TileSheet,
    ) -> None:
        assert test_case.group in shipped_sheet.table(test_case.table)
