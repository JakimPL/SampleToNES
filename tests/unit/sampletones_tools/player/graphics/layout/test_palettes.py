from dataclasses import dataclass
from typing import Final, Tuple

import pytest
from pydantic import ValidationError

from sampletones_player.specification.screen import (
    COLORS_PER_PALETTE,
    MASTER_COLOR_COUNT,
    PALETTE_SIZE,
    PALETTES_PER_LAYER,
)
from sampletones_tools.player.graphics.layout.palettes import PaletteColors, Palettes
from sampletones_tools.player.graphics.layout.screen import ScreenLayout
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase

StatedPalettes = Tuple[Tuple[int, ...], ...]

LAYER_SIZE: Final[int] = PALETTES_PER_LAYER * COLORS_PER_PALETTE
LAST_COLOR: Final[int] = MASTER_COLOR_COUNT - 1
COLOR_REFUSAL: Final[str] = "a palette names colors below"


def counting_from(first: int) -> Tuple[PaletteColors, ...]:
    """Four palettes whose colors count up from ``first``, so every entry is told from the next."""
    return tuple(
        (start, start + 1, start + 2, start + 3) for start in range(first, first + LAYER_SIZE, COLORS_PER_PALETTE)
    )


BACKGROUND: Final[Tuple[PaletteColors, ...]] = counting_from(0)
SPRITES: Final[Tuple[PaletteColors, ...]] = counting_from(LAYER_SIZE)


def recolored(color: int) -> Tuple[PaletteColors, ...]:
    """The background palettes with the last color of the last palette replaced."""
    last = BACKGROUND[-1]
    return (*BACKGROUND[:-1], (last[0], last[1], last[2], color))


class TestThePaletteMemory(BaseTestSuite):
    """The console keeps its background palettes ahead of its sprite palettes, four colors each."""

    def test_the_background_palettes_come_before_the_sprite_palettes(self) -> None:
        palettes = Palettes(background=BACKGROUND, sprites=SPRITES)

        assert palettes.to_bytes() == bytes(range(PALETTE_SIZE))

    def test_swapping_the_layers_swaps_the_halves_of_the_memory(self) -> None:
        stated = Palettes(background=BACKGROUND, sprites=SPRITES).to_bytes()
        swapped = Palettes(background=SPRITES, sprites=BACKGROUND).to_bytes()

        assert swapped == stated[LAYER_SIZE:] + stated[:LAYER_SIZE]

    def test_the_last_color_of_the_console_is_accepted(self) -> None:
        palettes = Palettes(background=recolored(LAST_COLOR), sprites=SPRITES)

        assert palettes.to_bytes()[LAYER_SIZE - 1] == LAST_COLOR

    def test_the_shipped_palettes_fill_the_palette_memory(self, shipped_layout: ScreenLayout) -> None:
        assert len(shipped_layout.palettes.to_bytes()) == PALETTE_SIZE

    def test_the_shipped_background_palettes_share_their_backdrop(self, shipped_layout: ScreenLayout) -> None:
        """A cell shows the backdrop wherever its tile is empty, whichever palette colors the cell."""
        backdrops = {palette[0] for palette in shipped_layout.palettes.background}

        assert len(backdrops) == 1


class TestAColorOutsideTheConsolesRange(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        color: int

    test_cases = (
        TestCase(color=MASTER_COLOR_COUNT, label="the color past the console's last"),
        TestCase(color=-1, label="the color before the console's first"),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_a_background_palette_naming_it_is_refused(self, test_case: TestCase) -> None:
        with pytest.raises(ValidationError, match=COLOR_REFUSAL):
            Palettes(background=recolored(test_case.color), sprites=SPRITES)

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_a_sprite_palette_naming_it_is_refused(self, test_case: TestCase) -> None:
        with pytest.raises(ValidationError, match=COLOR_REFUSAL):
            Palettes(background=BACKGROUND, sprites=recolored(test_case.color))


class TestALayerOfAnotherShape(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        palettes: StatedPalettes

    test_cases = (
        TestCase(palettes=BACKGROUND[:-1], label="a palette short"),
        TestCase(palettes=(*BACKGROUND, BACKGROUND[0]), label="a palette over"),
        TestCase(palettes=(), label="no palettes at all"),
        TestCase(palettes=(*BACKGROUND[:-1], BACKGROUND[-1][:-1]), label="a palette a color short"),
        TestCase(palettes=(*BACKGROUND[:-1], (*BACKGROUND[-1], 0)), label="a palette a color over"),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_background_layer_is_refused(self, test_case: TestCase) -> None:
        with pytest.raises(ValidationError, match="background"):
            Palettes.model_validate({"background": test_case.palettes, "sprites": SPRITES})

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_sprite_layer_is_refused(self, test_case: TestCase) -> None:
        with pytest.raises(ValidationError, match="sprites"):
            Palettes.model_validate({"background": BACKGROUND, "sprites": test_case.palettes})
