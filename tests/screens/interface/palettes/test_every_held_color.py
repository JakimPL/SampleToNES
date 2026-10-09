import operator
from typing import Dict, List, Tuple

from automation.palettes import Color, shared_colors, shipped_palettes
from automation.screen import Screen
from sampletones_application.utils.palette.catalog import DEFAULT_PALETTE_NAME
from tests.screens.interface.palettes.cases import Painted
from tests.screens.interface.palettes.constants import SETTLING_FRAMES
from tests.screens.interface.palettes.steps import painted, show_every_tab


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


class TestEveryHeldColorFollowsThePalette:
    """Picking a palette repaints every color the interface holds.

    A color that no palette changes is one every palette states alike. The table highlights follow the
    palette, a round trip comes back to the colors it began with, and Cancel puts back the palette
    in force before the preview.

    The scenario reads the starting palette, switches to each other palette and compares readings,
    returns to the first palette, then previews another one and cancels. It ends with the starting
    colors on the screen.
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
