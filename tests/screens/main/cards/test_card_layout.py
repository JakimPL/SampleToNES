import operator
from typing import Final, List

import pytest

from sampletones_application.constants.output import OutputKind
from sampletones_application.tags.main import (
    TAG_MAIN_ADVANCED_PANEL,
    TAG_MAIN_CONFIG_PANEL,
    TAG_MAIN_CONVERTER_PANEL,
    TAG_MAIN_SOURCE_PANEL,
)
from sampletones_application.utils.gui.shortcuts.ids import ShortcutId
from tests.suite.screens.dearpygui.geometry import Rect
from tests.suite.screens.dearpygui.items.reading import read_item
from tests.suite.screens.dearpygui.items.regions import read_scroll
from tests.suite.screens.screen import Screen
from tests.suite.screens.seeds.recordings import Recording
from tests.suite.screens.steps.main import gather, home_path
from tests.suite.screens.worlds.home import World
from tests.suite.screens.worlds.recordings import lived_in_world

PAST_THE_DIALOG: Final[int] = 30
SECONDS: Final[float] = 0.2
FREQUENCY: Final[float] = 220.0
SAME_LINE_PIXELS: Final[float] = 1.0


def box(screen: Screen, tag: str) -> Rect:
    """Returns the rectangle of the item ``tag``."""
    rect = screen.bridge.ask(lambda: read_item(tag).rect)
    assert rect is not None, tag
    return rect


def bottom(rect: Rect) -> float:
    """Returns the lower edge of ``rect``."""
    return rect.y + rect.height


def right(rect: Rect) -> float:
    """Returns the right edge of ``rect``."""
    return rect.x + rect.width


@pytest.fixture
def world() -> World:
    """The home holds thirty short voices, and the saved state shows the Advanced settings."""
    state = lived_in_world().state
    assert state is not None
    files = tuple(
        Recording(destination=home_path(f"voice{index:02d}.wav"), seconds=SECONDS, frequency=FREQUENCY)
        for index in range(PAST_THE_DIALOG)
    )
    return World(
        state=state.model_copy(update={"advanced_settings": True}),
        application_config=None,
        config=None,
        files=files,
    )


class TestTheCardsOfTheMainTab:
    """The Main tab stacks General settings, the Converter and Source settings from top to bottom, and the
    Advanced card keeps General's line.
    """

    def test_the_order_and_the_shared_line(self, screen: Screen) -> None:
        """The cards stand in order, General and Advanced end on one line, and Advanced lies right of
        General.
        """
        general = box(screen, TAG_MAIN_CONFIG_PANEL)
        advanced = box(screen, TAG_MAIN_ADVANCED_PANEL)
        converter = box(screen, TAG_MAIN_CONVERTER_PANEL)
        source = box(screen, TAG_MAIN_SOURCE_PANEL)

        assert general.y < converter.y < source.y
        assert abs(bottom(general) - bottom(advanced)) <= SAME_LINE_PIXELS
        assert right(general) < advanced.x

    def test_advanced_stands_beside_general_ending_where_the_converter_does(self, screen: Screen) -> None:
        """After Advanced is put away and shown again, it stands beside General and ends at the Converter's
        right edge.
        """

        def advanced_off_and_on_again(screen: Screen) -> None:
            screen.press_shortcut(ShortcutId.TOGGLE_ADVANCED_SETTINGS)
            screen.expect(screen.main.advanced.is_shown, operator.not_, description="Advanced put away")

            screen.press_shortcut(ShortcutId.TOGGLE_ADVANCED_SETTINGS)

            screen.expect(screen.main.advanced.is_shown, bool, description="Advanced back")

        def the_two_side_by_side(screen: Screen) -> None:
            screen.expect(
                lambda: right(box(screen, TAG_MAIN_CONFIG_PANEL)) < box(screen, TAG_MAIN_ADVANCED_PANEL).x,
                bool,
                description="the two side by side",
            )
            advanced = box(screen, TAG_MAIN_ADVANCED_PANEL)
            assert abs(right(advanced) - right(box(screen, TAG_MAIN_CONVERTER_PANEL))) <= SAME_LINE_PIXELS

        screen.scenario(advanced_off_and_on_again, the_two_side_by_side).run()

    @pytest.mark.xfail(
        strict=True,
        raises=AssertionError,
        reason="bugs-and-todos § Bugs: General settings stops short of the Converter's edge with Advanced put away",
    )
    def test_general_fills_the_row_with_advanced_put_away(self, screen: Screen) -> None:
        """With Advanced put away, General ends at the Converter's right edge."""
        screen.press_shortcut(ShortcutId.TOGGLE_ADVANCED_SETTINGS)
        screen.expect(screen.main.advanced.is_shown, operator.not_, description="Advanced put away")

        screen.expect(
            lambda: abs(right(box(screen, TAG_MAIN_CONFIG_PANEL)) - right(box(screen, TAG_MAIN_CONVERTER_PANEL))),
            lambda gap: gap <= SAME_LINE_PIXELS,
            description="General ending where the Converter does",
        )

    def test_collapsing_general_alone_gives_up_the_rows_height(self, screen: Screen) -> None:
        """Collapsing General with Advanced put away shrinks the card and lifts the Converter to meet it."""
        general = screen.main.card(TAG_MAIN_CONFIG_PANEL)
        heights: List[float] = []

        def put_advanced_away(screen: Screen) -> None:
            screen.press_shortcut(ShortcutId.TOGGLE_ADVANCED_SETTINGS)
            screen.expect(screen.main.advanced.is_shown, operator.not_, description="Advanced put away")
            heights.append(box(screen, TAG_MAIN_CONFIG_PANEL).height)

        def collapse_general(screen: Screen) -> None:
            general.toggle()

            screen.expect(general.is_collapsed, bool, description="General collapsed")
            screen.expect(
                lambda: box(screen, TAG_MAIN_CONVERTER_PANEL).y - bottom(box(screen, TAG_MAIN_CONFIG_PANEL)),
                lambda gap: gap < heights[0],
                description="the Converter meeting the collapsed card",
            )
            collapsed = box(screen, TAG_MAIN_CONFIG_PANEL)
            assert collapsed.height < heights[0]

        screen.scenario(put_advanced_away, collapse_general).run()


class TestAddingAfterScrollingThePick:
    """A mix picked from a scrolled list closes on Add, and the card answers the next gesture.

    The checklist asks it of twelve recordings. The question fits twelve without scrolling on this
    screen, so the scenario gathers as many as make it scroll. It scrolls the pick list to the end and
    presses Add. A click on the first row then shows that recording on the Source card.
    """

    def test_the_question_closes_and_the_card_answers(self, screen: Screen) -> None:
        """Add closes the question and the next row pick reaches the Source card."""
        main = screen.main
        question = main.converter.mix_question
        paths = [home_path(f"voice{index:02d}.wav") for index in range(PAST_THE_DIALOG)]

        def open_the_question_and_scroll_it(screen: Screen) -> None:
            gather(screen, *paths)
            main.choose_output(OutputKind.MIXED)
            screen.expect(question.is_shown, bool, description="the question")
            screen.expect(
                lambda: screen.bridge.ask(lambda: read_scroll(question.tags.well)).maximum,
                lambda maximum: maximum > 0,
                description="the pick list scrolling",
            )

            screen.hand.scroll_to_end(question.tags.well)

        def add(screen: Screen) -> None:
            question.add()

            screen.expect(question.is_shown, operator.not_, description="the question closed")

        def the_card_answers(screen: Screen) -> None:
            main.converter.list.pick(paths[0])

            screen.expect(main.source.subject, paths[0].stem.__eq__, description="the card on the row picked")

        screen.scenario(open_the_question_and_scroll_it, add, the_card_answers).run()
