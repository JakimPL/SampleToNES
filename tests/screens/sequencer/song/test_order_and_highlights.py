import operator
from functools import partial
from typing import Final

from sampletones_application.view_model.sequencer.subcolumn import SubColumn
from sampletones_core.constants.enums import ChannelName
from tests.screens.sequencer.song.constants import EMPTY_VOICE, LINE_NUMBER
from tests.suite.screens.screen import Screen
from tests.suite.screens.steps.sequencer import leave_letting_the_project_go, on_the_sequencer

FIRST_PATTERN: Final[str] = "00"
SECOND_PATTERN: Final[str] = "01"
FIRST_HIGHLIGHT: Final[int] = 3
SECOND_HIGHLIGHT: Final[int] = 6
TINTED_ROWS_READ: Final[int] = 13


class TestTheOrderTable:
    """Typing an order entry names the pattern a channel plays at that frame, and the tracker follows it.

    Pattern 01 typed on the first frame of the first pulse channel empties its first line; typing 00 again
    brings the line back.
    """

    def test_patterns_follow_the_order(self, screen: Screen) -> None:
        """The tracker shows the pattern the order entry names."""
        order = screen.sequencer.order
        tracker = screen.sequencer.tracker

        def a_new_pattern_number_shows_a_new_pattern(screen: Screen) -> None:
            on_the_sequencer(screen)
            assert order.label(ChannelName.PULSE1, 0) == FIRST_PATTERN
            order.click(ChannelName.PULSE1, 0)

            screen.hand.type_text(SECOND_PATTERN)

            screen.expect(partial(order.label, ChannelName.PULSE1, 0), SECOND_PATTERN.__eq__, description="pattern 01")
            assert tracker.label(0, ChannelName.PULSE1, SubColumn.VOICE) == EMPTY_VOICE

        def the_first_number_brings_the_line_back(screen: Screen) -> None:
            order.click(ChannelName.PULSE1, 0)

            screen.hand.type_text(FIRST_PATTERN)

            screen.expect(partial(order.label, ChannelName.PULSE1, 0), FIRST_PATTERN.__eq__, description="pattern 00")
            screen.expect(
                partial(tracker.label, 0, ChannelName.PULSE1, SubColumn.VOICE),
                LINE_NUMBER.__eq__,
                description="the line back",
            )

        screen.scenario(
            a_new_pattern_number_shows_a_new_pattern,
            the_first_number_brings_the_line_back,
            leave_letting_the_project_go,
        ).run()


class TestTheHighlights:
    """The tracker tints the rows the project's highlights name.

    Highlights of three and six are typed in Project properties; every third row ends up tinted.
    """

    def test_rows_on_the_highlight_are_tinted(self, screen: Screen) -> None:
        """Exactly the rows on the first highlight are tinted."""
        properties = screen.project.properties
        tracker = screen.sequencer.tracker

        def set_highlights_of_three_and_six(screen: Screen) -> None:
            on_the_sequencer(screen)
            properties.open()
            screen.expect(properties.is_shown, bool, description="Project properties")

            properties.retype_highlights(FIRST_HIGHLIGHT, SECOND_HIGHLIGHT)
            properties.confirm()

            screen.expect(properties.is_shown, operator.not_, description="Project properties closed")

        def every_third_row_is_tinted(screen: Screen) -> None:
            expected = [row % FIRST_HIGHLIGHT == 0 for row in range(TINTED_ROWS_READ)]

            screen.expect(
                lambda: [tracker.is_row_tinted(row) for row in range(TINTED_ROWS_READ)],
                expected.__eq__,
                description="every third row tinted",
            )

        screen.scenario(set_highlights_of_three_and_six, every_third_row_is_tinted, leave_letting_the_project_go).run()
