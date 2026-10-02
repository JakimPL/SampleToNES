import operator
from dataclasses import dataclass
from typing import Dict, Final, List, Tuple

import pytest

from sampletones_application.categories.hierarchy import Tab
from sampletones_application.utils.palette.catalog import DEFAULT_PALETTE_NAME
from tests.suite.screens.application import Startup
from tests.suite.screens.boundaries.highlights import HighlightPlace
from tests.suite.screens.dearpygui.items import read_held_colors
from tests.suite.screens.palettes import Color, in_fractions, shared_colors, shipped_palettes
from tests.suite.screens.screen import Screen
from tests.suite.screens.steps.reconstructions import expect_open
from tests.suite.screens.world import ARRANGED_PROJECT, PLAYABLE_RECONSTRUCTION

SETTLING_FRAMES: Final[int] = 10
TAB_FRAMES: Final[int] = 10
EVERY_TAB: Final[Tuple[Tab, ...]] = (Tab.MAIN, Tab.INSTRUCTIONS, Tab.RECONSTRUCTIONS, Tab.SEQUENCER)
SECOND_ROUND: Final[int] = 2
ROUNDS: Final[int] = 20


@dataclass(frozen=True)
class Painted:
    """Every color the interface holds at one moment: what DearPyGui holds for items and themes, and the highlights
    laid on its tables.
    """

    held: Dict[str, Color]
    highlights: Dict[HighlightPlace, Color]


def painted(screen: Screen) -> Painted:
    return Painted(
        held=screen.bridge.ask(read_held_colors),
        highlights={place: in_fractions(color) for place, color in screen.table_highlights().items()},
    )


def unchanged(readings: List[Painted]) -> Tuple[List[Color], List[Color]]:
    """The held colors and the highlight colors that read the same in every reading."""
    held = [readings[0].held[key] for key in readings[0].held if len({reading.held[key] for reading in readings}) == 1]
    highlights = [
        readings[0].highlights[place]
        for place in readings[0].highlights
        if len({reading.highlights[place] for reading in readings}) == 1
    ]
    return held, highlights


def differing(after: Painted, before: Painted) -> Dict[str, Tuple[Color, Color]]:
    """The held colors two readings disagree on, among the items both found drawn.

    A dialog closed between the readings takes its own items off the screen, so those are left out.
    """
    common = after.held.keys() & before.held.keys()
    assert len(common) > len(before.held) // 2
    return {key: (after.held[key], before.held[key]) for key in common if after.held[key] != before.held[key]}


@pytest.fixture
def startup() -> Startup:
    return Startup(reconstruction=PLAYABLE_RECONSTRUCTION, project=ARRANGED_PROJECT)


def show_every_tab(screen: Screen) -> None:
    """Brings each tab forward once, so every panel stands built and drawn before the colors are read."""
    expect_open(screen, PLAYABLE_RECONSTRUCTION)
    for tab in EVERY_TAB:
        screen.tabs.bring_to_front(tab)
        screen.frames(TAB_FRAMES)


class TestEveryHeldColorFollowsThePalette:
    """A palette picked repaints every color the interface holds: what no palette changes is a color every palette
    states alike, the table highlights follow, a round trip comes back to where it began, and Cancel leaves nothing
    of the palette it previewed.
    """

    def test_no_color_is_left_from_the_palette_before(self, screen: Screen) -> None:
        settings = screen.display_settings
        catalog = shipped_palettes()
        readings: Dict[str, Painted] = {}

        def read_the_palette_the_application_starts_in(screen: Screen) -> None:
            show_every_tab(screen)
            settings.open()
            screen.expect(settings.is_shown, bool, description="Display settings")

            assert settings.palette() == DEFAULT_PALETTE_NAME
            readings[DEFAULT_PALETTE_NAME] = painted(screen)
            assert readings[DEFAULT_PALETTE_NAME].highlights

        def every_palette_repaints_what_differs(screen: Screen) -> None:
            for name in catalog.names:
                if name == DEFAULT_PALETTE_NAME:
                    continue

                settings.choose_palette(name)
                screen.frames(SETTLING_FRAMES)
                readings[name] = painted(screen)
                assert readings[name].held.keys() == readings[DEFAULT_PALETTE_NAME].held.keys()
                assert readings[name].highlights.keys() == readings[DEFAULT_PALETTE_NAME].highlights.keys()

            held, highlights = unchanged(list(readings.values()))
            assert set(held) <= shared_colors(catalog)
            assert set(highlights) <= shared_colors(catalog)

        def the_first_palette_again_paints_as_it_began(screen: Screen) -> None:
            settings.choose_palette(DEFAULT_PALETTE_NAME)
            screen.frames(SETTLING_FRAMES)

            assert painted(screen) == readings[DEFAULT_PALETTE_NAME]

        def cancel_leaves_nothing_of_the_preview(screen: Screen) -> None:
            other = next(name for name in catalog.names if name != DEFAULT_PALETTE_NAME)
            settings.choose_palette(other)
            screen.frames(SETTLING_FRAMES)
            assert painted(screen) == readings[other]

            settings.cancel()
            screen.expect(settings.discard_prompt.is_shown, bool, description="the question about the change")
            settings.discard_prompt.confirm()

            screen.expect(settings.is_shown, operator.not_, description="Display settings closed")
            screen.frames(SETTLING_FRAMES)
            after = painted(screen)
            assert after.highlights == readings[DEFAULT_PALETTE_NAME].highlights
            assert differing(after, readings[DEFAULT_PALETTE_NAME]) == {}

        screen.scenario(
            read_the_palette_the_application_starts_in,
            every_palette_repaints_what_differs,
            the_first_palette_again_paints_as_it_began,
            cancel_leaves_nothing_of_the_preview,
        ).run()


class TestTwentySwaps:
    """Twenty round trips between two palettes build nothing: the interface holds as many items after the twentieth
    as after the second, and paints as it did.
    """

    def test_the_item_count_holds(self, screen: Screen) -> None:
        settings = screen.display_settings
        catalog = shipped_palettes()
        other = next(name for name in catalog.names if name != DEFAULT_PALETTE_NAME)
        counts: Dict[int, int] = {}
        readings: List[Painted] = []

        def swap_back_and_forth(screen: Screen) -> None:
            show_every_tab(screen)
            settings.open()
            screen.expect(settings.is_shown, bool, description="Display settings")
            readings.append(painted(screen))

            for round_number in range(1, ROUNDS + 1):
                settings.choose_palette(other)
                settings.choose_palette(DEFAULT_PALETTE_NAME)
                screen.frames(SETTLING_FRAMES)
                counts[round_number] = screen.item_count()

            assert counts[ROUNDS] == counts[SECOND_ROUND]
            assert painted(screen) == readings[0]
            settings.cancel()
            screen.expect(settings.is_shown, operator.not_, description="Display settings closed")

        screen.scenario(swap_back_and_forth).run()
