import operator
from typing import Final, List

from automation.dearpygui.geometry import Rect
from automation.screen import Screen
from automation.steps.main import explorer_row, home_path
from tests.screens.main.gathering.steps import gathered
from tests.suite.screens.seeds.constants import KICK, SNARE

ROUNDS: Final[int] = 20
FIRST_COUNTED_ROUND: Final[int] = 2
POINTER_REACH: Final[int] = 4


class TestRightClickingOverAndOver:
    """Twenty right-clicks, alternating between the explorer and the list, each open a menu at the pointer
    and leave the interface as large as it was.

    A recording is gathered first. Each round opens the menu, reads its box and entries and dismisses
    it. The scenario ends when the item count of the last round equals that of the second round.
    """

    def test_each_menu_stands_at_the_pointer_and_the_interface_does_not_grow(self, screen: Screen) -> None:
        """Each menu overlaps the pointer, has labeled entries and the item count stays level."""
        converter = screen.main.converter
        menu = screen.context_menu
        counts: List[int] = []

        def gather(screen: Screen) -> None:
            screen.explorer.double_click(explorer_row(screen, home_path(KICK)))
            gathered(screen, home_path(KICK))

        def right_click_over_and_over(screen: Screen) -> None:
            for round_number in range(1, ROUNDS + 1):
                in_the_list = round_number % 2 == 0
                row = converter.list.row(home_path(KICK)) if in_the_list else explorer_row(screen, home_path(SNARE))
                if in_the_list:
                    screen.hand.scroll_into_view(row)
                    screen.hand.right_click(row)
                else:
                    screen.explorer.right_click(row)
                screen.expect(menu.is_shown, bool, description=f"the menu of round {round_number}")
                pointer = screen.pointer()

                box = menu.box()
                entries = menu.entries()
                menu.dismiss()

                screen.expect(menu.is_shown, operator.not_, description=f"the menu of round {round_number} put away")
                assert (
                    box.overlap(
                        Rect(
                            x=pointer.x - POINTER_REACH,
                            y=pointer.y - POINTER_REACH,
                            width=2 * POINTER_REACH,
                            height=2 * POINTER_REACH,
                        )
                    )
                    is not None
                ), (box, pointer)
                assert entries and all(entry.enabled or entry.label for entry in entries)
                if round_number >= FIRST_COUNTED_ROUND:
                    counts.append(screen.item_count())

        def nothing_grew(screen: Screen) -> None:
            assert counts[-1] == counts[0], counts

        screen.scenario(gather, right_click_over_and_over, nothing_grew).run()
