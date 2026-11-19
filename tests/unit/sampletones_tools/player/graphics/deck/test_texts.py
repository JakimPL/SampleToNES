from dataclasses import dataclass
from typing import Final, List

import pytest

from sampletones_core.constants.general import MAX_PERIOD
from sampletones_core.utils.frequencies import period_to_name, pitch_to_name
from sampletones_player.compression.pitch import PITCH_COUNT
from sampletones_shared.constants.music import LIMIT_MIN_PITCH
from sampletones_tools.player.graphics.deck.groups import BAR_GROUP
from sampletones_tools.player.graphics.deck.state import NOISE_PERIOD_COUNT
from sampletones_tools.player.graphics.deck.texts import (
    REST_NOTE,
    SECONDS_PER_MINUTE,
    UNKNOWN_CHARACTER,
    clock_text,
    noise_name,
    pitch_name,
)
from sampletones_tools.player.graphics.layout.screen import TEXT_GROUP
from sampletones_tools.player.graphics.sheet.groups import PatternTable
from sampletones_tools.player.graphics.sheet.sheet import TileSheet
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase

PITCHES: Final[range] = range(PITCH_COUNT)
PERIODS: Final[range] = range(NOISE_PERIOD_COUNT)
CLOCK_MINUTES: Final[int] = 100


def pitch_names() -> List[str]:
    return [pitch_name(pitch) for pitch in PITCHES]


def noise_names() -> List[str]:
    return [noise_name(period) for period in PERIODS]


class TestTheNameOfAPitch(BaseTestSuite):
    def test_every_pitch_is_named_the_way_the_application_names_it(self) -> None:
        assert pitch_names() == [pitch_to_name(LIMIT_MIN_PITCH + pitch) for pitch in PITCHES]

    def test_every_name_is_as_wide_as_the_rest_note(self) -> None:
        assert {len(name) for name in pitch_names()} == {len(REST_NOTE)}

    def test_every_pitch_has_a_name_of_its_own(self) -> None:
        assert len(set(pitch_names())) == PITCH_COUNT


class TestTheNameOfANoisePeriod(BaseTestSuite):
    def test_every_period_is_named_the_way_the_application_names_it(self) -> None:
        assert noise_names() == [period_to_name(MAX_PERIOD - period) for period in PERIODS]

    def test_every_name_is_as_wide_as_the_rest_note(self) -> None:
        assert {len(name) for name in noise_names()} == {len(REST_NOTE)}

    def test_every_period_has_a_name_of_its_own(self) -> None:
        assert len(set(noise_names())) == NOISE_PERIOD_COUNT


class TestAClock(BaseTestSuite):
    """Minutes and seconds in two digits each is the clock's own format, so the cases spell it out."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        seconds: int
        expected: str

    test_cases = (
        TestCase(seconds=0, expected="00:00", label="no time at all"),
        TestCase(seconds=5, expected="00:05", label="a few seconds"),
        TestCase(seconds=59, expected="00:59", label="a second short of a minute"),
        TestCase(seconds=60, expected="01:00", label="a whole minute"),
        TestCase(seconds=83, expected="01:23", label="a minute and some seconds"),
        TestCase(seconds=600, expected="10:00", label="ten minutes"),
        TestCase(seconds=3599, expected="59:59", label="a second short of an hour"),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_minutes_and_seconds_take_two_digits_each(self, test_case: TestCase) -> None:
        assert clock_text(test_case.seconds) == test_case.expected


class TestTheTextsOnTheShippedSheet(BaseTestSuite):
    def test_every_note_is_spelled_in_characters_the_text_group_draws(self, shipped_sheet: TileSheet) -> None:
        spelled = set("".join([*pitch_names(), *noise_names(), REST_NOTE]))

        assert spelled <= set(shipped_sheet.table(PatternTable.BACKGROUND)[TEXT_GROUP].characters)

    def test_the_character_standing_for_an_unknown_one_is_drawn(self, shipped_sheet: TileSheet) -> None:
        assert UNKNOWN_CHARACTER in shipped_sheet.table(PatternTable.BACKGROUND)[TEXT_GROUP].characters

    def test_every_clock_is_spelled_in_characters_the_bar_draws(self, shipped_sheet: TileSheet) -> None:
        spelled = set("".join(clock_text(seconds) for seconds in range(CLOCK_MINUTES * SECONDS_PER_MINUTE)))

        assert spelled <= set(shipped_sheet.table(PatternTable.BACKGROUND)[BAR_GROUP].characters)
