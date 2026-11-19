from typing import Final, List, Tuple

from sampletones_tools.player.graphics.deck.groups import CHROME_GROUP, TileName
from sampletones_tools.player.graphics.deck.state import DUTY_COUNT
from sampletones_tools.player.graphics.deck.waves import (
    BLANK,
    NOISE_WAVES,
    OTHER_REST,
    PULSE_REST,
    PULSE_WAVES,
    TRIANGLE_WAVE,
    Wave,
)
from sampletones_tools.player.graphics.sheet.groups import PatternTable
from sampletones_tools.player.graphics.sheet.sheet import TileSheet
from tests.suite.base import BaseTestSuite

GROUP: Final[str] = "curves"
LONG: Final[bool] = False
SHORT: Final[bool] = True
NOISE_SHAPES: Final[Tuple[Wave, ...]] = (*NOISE_WAVES[LONG], *NOISE_WAVES[SHORT])
EVERY_SHAPE: Final[Tuple[Wave, ...]] = (*PULSE_WAVES, PULSE_REST, OTHER_REST, TRIANGLE_WAVE, *NOISE_SHAPES)


def names_of(wave: Wave) -> Tuple[TileName, ...]:
    return (*wave.top, *wave.bottom)


class TestAWaveOfOneGroup(BaseTestSuite):
    def test_every_member_is_named_with_the_group(self) -> None:
        wave = Wave.of(GROUP, ("rise", "fall"), ("dip", "climb"))

        assert wave.top == (TileName(GROUP, "rise"), TileName(GROUP, "fall"))
        assert wave.bottom == (TileName(GROUP, "dip"), TileName(GROUP, "climb"))

    def test_a_tile_the_wave_leaves_empty_is_the_blank_tile_of_the_chrome(self) -> None:
        wave = Wave.of(GROUP, (BLANK.member, "fall"), ("dip", BLANK.member))

        assert (wave.top[0], wave.bottom[1]) == (BLANK, BLANK)
        assert BLANK.group == CHROME_GROUP


class TestTheShapesTheChannelsDraw(BaseTestSuite):
    def test_the_shipped_sheet_draws_every_tile_a_shape_names(self, shipped_sheet: TileSheet) -> None:
        background = shipped_sheet.table(PatternTable.BACKGROUND)

        undrawn: List[TileName] = [
            name for wave in EVERY_SHAPE for name in names_of(wave) if name.member not in background[name.group].members
        ]

        assert not undrawn

    def test_every_duty_cycle_has_a_shape_of_its_own(self) -> None:
        assert len(PULSE_WAVES) == DUTY_COUNT
        assert len(set(PULSE_WAVES)) == DUTY_COUNT

    def test_a_sounding_pulse_draws_another_shape_than_a_resting_one(self) -> None:
        assert PULSE_REST not in PULSE_WAVES

    def test_a_sounding_triangle_draws_another_shape_than_a_resting_one(self) -> None:
        assert TRIANGLE_WAVE != OTHER_REST

    def test_a_sounding_noise_draws_another_shape_than_a_resting_one(self) -> None:
        assert OTHER_REST not in NOISE_SHAPES

    def test_each_noise_sequence_shimmers_between_two_arrangements(self) -> None:
        for sequence in (LONG, SHORT):
            still, moved = NOISE_WAVES[sequence]
            assert still != moved

    def test_the_short_sequence_draws_other_shapes_than_the_long_one(self) -> None:
        assert not set(NOISE_WAVES[LONG]) & set(NOISE_WAVES[SHORT])
