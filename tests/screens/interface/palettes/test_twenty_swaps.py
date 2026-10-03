import operator
from typing import Dict, Final, List

from sampletones_application.utils.palette.catalog import DEFAULT_PALETTE_NAME
from tests.screens.interface.palettes.cases import Painted
from tests.screens.interface.palettes.constants import SETTLING_FRAMES
from tests.screens.interface.palettes.steps import painted, show_every_tab
from tests.suite.screens.palettes import shipped_palettes
from tests.suite.screens.screen import Screen

SECOND_ROUND: Final[int] = 2
ROUNDS: Final[int] = 20


class TestTwentySwaps:
    """Twenty round trips between two palettes add no items: the interface holds as many items after the
    twentieth as after the second, and paints as it did.
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
