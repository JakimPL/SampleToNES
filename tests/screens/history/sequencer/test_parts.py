import operator
from typing import Callable, Final, List, Tuple, TypeVar

from sampletones_application.categories.hierarchy import Tab
from sampletones_application.constants.sequencer import CHANNEL_AXIS
from sampletones_application.utils.gui.shortcuts.ids import ShortcutId
from sampletones_application.view_model.sequencer.subcolumn import SubColumn
from sampletones_core.constants.enums import ChannelName
from tests.screens.history.steps import expect_lines, history_count, press_on_the_sequencer
from tests.suite.screens.screen import Screen
from tests.suite.screens.steps.project import retitle_project
from tests.suite.screens.steps.sequencer import leave_letting_the_project_go

ReadingT = TypeVar("ReadingT")

GRID_ROWS: Final[range] = range(8)
GRID_CHANNELS: Final[Tuple[ChannelName, ...]] = (ChannelName.PULSE1, ChannelName.PULSE2)
TYPED_VOLUME: Final[str] = "5"
ORDER_CHANNEL: Final[ChannelName] = ChannelName.PULSE1
ORDER_POSITION: Final[int] = 1
TEMPO: Final[int] = 120
SPEED: Final[int] = 3
ROWS: Final[int] = 12
RETITLED: Final[str] = "Retitled history"
STILL_FRAMES: Final[int] = 20


def walk_back_and_forth(
    screen: Screen,
    reading: Callable[[], ReadingT],
    states: List[ReadingT],
) -> None:
    """Undoes every gesture one by one, redoes them all, then jumps to the oldest and the newest line,
    reading ``states[index]`` after each step that leaves the project at entry ``index``.
    """
    history = screen.sequencer.history
    newest = len(states) - 1
    for index in range(newest - 1, -1, -1):
        press_on_the_sequencer(screen, ShortcutId.UNDO)
        screen.expect(reading, states[index].__eq__, description=f"the state of entry {index}")

    for index in range(1, newest + 1):
        press_on_the_sequencer(screen, ShortcutId.REDO)
        screen.expect(reading, states[index].__eq__, description=f"the state of entry {index} again")

    history.jump_to(history_count(screen) - 1)
    screen.expect(reading, states[0].__eq__, description="the oldest line's state")
    history.jump_to(0)
    screen.expect(reading, states[newest].__eq__, description="the newest line's state")


def gesture_adding_a_line(
    screen: Screen,
    gesture: Callable[[], None],
) -> None:
    """Runs ``gesture`` and waits for the one line it adds to the History card."""
    lines = history_count(screen)
    gesture()
    expect_lines(screen, lines + 1)


class TestTheTrackerCells:
    """Each gesture on the tracker's cells is one entry, and every way back and forth shows each grid again.

    A volume is typed, a row cleared, a pitch transposed, a volume lowered, and a cell cut and pasted
    elsewhere, each adding one line; then every step is undone, redone and jumped to.
    """

    def test_every_grid_comes_back(self, screen: Screen) -> None:
        tracker = screen.sequencer.tracker
        grids: List[Tuple[Tuple[str, ...], ...]] = []

        def grid() -> Tuple[Tuple[str, ...], ...]:
            return tuple(tracker.labels(row, channel) for row in GRID_ROWS for channel in GRID_CHANNELS)

        def at(
            row: int,
            channel: ChannelName,
            subcolumn: SubColumn,
            then: Callable[[], None],
        ) -> Callable[[], None]:
            def gesture() -> None:
                tracker.click(row, channel, subcolumn)
                then()

            return gesture

        def edit_the_cells(screen: Screen) -> None:
            screen.tabs.bring_to_front(Tab.SEQUENCER)
            grids.append(grid())
            for gesture in (
                at(1, ChannelName.PULSE1, SubColumn.VOLUME, lambda: screen.hand.type_text(TYPED_VOLUME)),
                at(0, ChannelName.PULSE2, SubColumn.VOICE, lambda: screen.press_shortcut(ShortcutId.TRACKER_CLEAR_ROW)),
                at(
                    2,
                    ChannelName.PULSE1,
                    SubColumn.TRANSPOSE,
                    lambda: screen.press_shortcut(ShortcutId.TRACKER_TRANSPOSE_UP),
                ),
                at(
                    6,
                    ChannelName.PULSE1,
                    SubColumn.VOLUME,
                    lambda: screen.press_shortcut(ShortcutId.TRACKER_VOLUME_DOWN),
                ),
                at(6, ChannelName.PULSE1, SubColumn.VOICE, lambda: screen.press_shortcut(ShortcutId.TRACKER_CUT_BLOCK)),
                at(
                    3,
                    ChannelName.PULSE2,
                    SubColumn.VOICE,
                    lambda: screen.press_shortcut(ShortcutId.TRACKER_PASTE_BLOCK),
                ),
            ):
                gesture_adding_a_line(screen, gesture)
                grids.append(screen.expect(grid, grids[-1].__ne__, description="the grid changed"))

        def walk(screen: Screen) -> None:
            walk_back_and_forth(screen, grid, grids)

        screen.scenario(edit_the_cells, walk, leave_letting_the_project_go).run()


class TestTheOrderFrames:
    """Each gesture on the song's frames is one entry, and every way back and forth shows each order again.

    A frame is added, duplicated, cloned and cleared from the order table's keys, each adding one line;
    then every step is undone, redone and jumped to.
    """

    def test_every_order_comes_back(self, screen: Screen) -> None:
        order = screen.sequencer.order
        orders: List[Tuple[Tuple[str, ...], ...]] = []

        def table() -> Tuple[Tuple[str, ...], ...]:
            positions = order.positions()
            return tuple(
                tuple(order.label(channel, position) for position in range(positions)) for channel in CHANNEL_AXIS
            )

        def pressing(shortcut_id: ShortcutId) -> Callable[[], None]:
            def gesture() -> None:
                order.click(ORDER_CHANNEL, ORDER_POSITION)
                screen.press_shortcut(shortcut_id)

            return gesture

        def edit_the_frames(screen: Screen) -> None:
            screen.tabs.bring_to_front(Tab.SEQUENCER)
            orders.append(table())
            for shortcut_id in (
                ShortcutId.ORDER_ADD_FRAME,
                ShortcutId.ORDER_DUPLICATE_FRAME,
                ShortcutId.ORDER_CLONE_FRAME,
                ShortcutId.ORDER_CLEAR_FRAME,
            ):
                gesture_adding_a_line(screen, pressing(shortcut_id))
                orders.append(screen.expect(table, orders[-1].__ne__, description="the order changed"))

        def walk(screen: Screen) -> None:
            walk_back_and_forth(screen, table, orders)

        screen.scenario(edit_the_frames, walk, leave_letting_the_project_go).run()


class TestTheModuleValues:
    """Tempo, speed and rows per pattern are one entry each, which every way back and forth shows again."""

    def test_every_value_comes_back(self, screen: Screen) -> None:
        module = screen.sequencer.module
        values: List[Tuple[int, int, int]] = []

        def read() -> Tuple[int, int, int]:
            return module.tempo(), module.speed(), module.rows()

        def retype_each(screen: Screen) -> None:
            screen.tabs.bring_to_front(Tab.SEQUENCER)
            values.append(read())
            for gesture in (
                lambda: module.retype_tempo(TEMPO),
                lambda: module.retype_speed(SPEED),
                lambda: module.retype_rows(ROWS),
            ):
                gesture_adding_a_line(screen, gesture)
                values.append(screen.expect(read, values[-1].__ne__, description="the value changed"))

        def walk(screen: Screen) -> None:
            walk_back_and_forth(screen, read, values)

        screen.scenario(retype_each, walk, leave_letting_the_project_go).run()


class TestTheProjectProperties:
    """A title confirmed in Project properties is one entry, Undo brings the old title back, and confirming
    the dialog unchanged adds nothing.

    The project is retitled, which adds a line. After an undo the dialog shows the old title, and confirming
    it as it stands leaves the card as it was; retitling again then puts a line in force over the one undone,
    which witnesses the dialog.
    """

    def test_the_title_comes_back(self, screen: Screen) -> None:
        properties = screen.project.properties
        titles: List[str] = []

        def read_the_title(screen: Screen) -> str:
            properties.open()
            screen.expect(properties.is_shown, bool, description="the Project properties dialog")
            return properties.title()

        def retitle(screen: Screen) -> None:
            screen.tabs.bring_to_front(Tab.SEQUENCER)
            titles.append(read_the_title(screen))
            properties.confirm()
            screen.expect(properties.is_shown, operator.not_, description="the dialog closed")

            gesture_adding_a_line(screen, lambda: retitle_project(screen, RETITLED))

        def undo_brings_the_title_back(screen: Screen) -> None:
            press_on_the_sequencer(screen, ShortcutId.UNDO)
            screen.expect(lambda: screen.sequencer.history.lines()[-1].current, bool, description="one step back")

            assert read_the_title(screen) == titles[0]

        def confirming_it_unchanged_adds_nothing(screen: Screen) -> None:
            lines = history_count(screen)

            properties.confirm()

            screen.expect(properties.is_shown, operator.not_, description="the dialog closed")
            screen.frames(STILL_FRAMES)
            assert history_count(screen) == lines
            assert not screen.sequencer.history.lines()[0].current

            retitle_project(screen, RETITLED)

            screen.expect(lambda: screen.sequencer.history.lines()[0].current, bool, description="the retitle in force")
            assert history_count(screen) == lines

        screen.scenario(
            retitle,
            undo_brings_the_title_back,
            confirming_it_unchanged_adds_nothing,
            leave_letting_the_project_go,
        ).run()
