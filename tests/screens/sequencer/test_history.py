import operator
from functools import partial
from typing import Callable, Final, List, Tuple

import pytest

from sampletones_application.categories.hierarchy import Tab
from sampletones_application.tags.sequencer import TAG_SEQUENCER_VOICES_INPUT_RENAME
from sampletones_application.utils.gui.shortcuts.ids import ShortcutId
from sampletones_core.constants.enums import ChannelName, FeatureKey
from tests.suite.screens.application import Startup
from tests.suite.screens.dearpygui.items import read_item
from tests.suite.screens.dearpygui.keys import IMGUI_ENTER
from tests.suite.screens.screen import Screen
from tests.suite.screens.steps.reconstructions import titled
from tests.suite.screens.steps.sequencer import open_voice
from tests.suite.screens.views.history import HistoryLine
from tests.suite.screens.world import ARRANGED_PROJECT, BASS_VOICE, LINE, PAD

SETTLING_FRAMES: Final[int] = 10
RENAMED: Final[str] = "Renamed"
DUPLICATE: Final[str] = "sequencer.voices.label.context_duplicate"
HOVER_RACE: Final[str] = "Error executing callback _on_row_hovered"
VOLUME_LETTER: Final[str] = "v"
ARPEGGIO_LETTER: Final[str] = "a"
QUIET: Final[float] = 4.0
ARPEGGIO_STEP: Final[float] = 5.0
DRAGGED_ITEM: Final[int] = 1
LINE_POSITION: Final[str] = "00"
PAD_POSITION: Final[str] = "02"
POSITION_MARK: Final[str] = ":"

Gesture = Callable[[Screen, str], None]


@pytest.fixture
def startup() -> Startup:
    return Startup(reconstruction=None, project=ARRANGED_PROJECT)


def pick(screen: Screen, name: str) -> None:
    voices = screen.sequencer.voices
    screen.tabs.bring_to_front(Tab.SEQUENCER)
    row = screen.expect_item(partial(voices.row, name), description=f"the row of {name}")
    voices.pick(row)
    screen.frames(SETTLING_FRAMES)


def rename(screen: Screen, name: str) -> None:
    pick(screen, name)
    screen.press_shortcut(ShortcutId.VOICES_RENAME_VOICE)
    screen.expect(
        lambda: screen.bridge.ask(lambda: read_item(TAG_SEQUENCER_VOICES_INPUT_RENAME)).shown,
        bool,
        description="the name being edited",
    )

    screen.hand.replace_text(TAG_SEQUENCER_VOICES_INPUT_RENAME, RENAMED)
    screen.hand.press_key(IMGUI_ENTER, modifiers=[])


def duplicate(screen: Screen, name: str) -> None:
    voices = screen.sequencer.voices
    menu = screen.context_menu
    screen.tabs.bring_to_front(Tab.SEQUENCER)
    voices.right_click(screen.expect_item(partial(voices.row, name), description=f"the row of {name}"))
    screen.expect(menu.is_shown, bool, description="the row's menu")
    menu.choose(screen.words(DUPLICATE))


def move_down(screen: Screen, name: str) -> None:
    pick(screen, name)
    screen.press_shortcut(ShortcutId.VOICES_MOVE_VOICE_DOWN)


def move(screen: Screen, name: str) -> None:
    """Moves the voice ``name`` one place, down where a place lies below it and up otherwise."""
    last = screen.sequencer.voices.names()[-1] == name
    pick(screen, name)
    screen.press_shortcut(ShortcutId.VOICES_MOVE_VOICE_UP if last else ShortcutId.VOICES_MOVE_VOICE_DOWN)


def remove(screen: Screen, name: str) -> None:
    prompt = screen.sequencer.voices.remove_prompt
    pick(screen, name)
    screen.press_shortcut(ShortcutId.VOICES_REMOVE_VOICE)
    screen.expect(prompt.is_shown, bool, description="the question about removing")
    prompt.confirm()
    screen.expect(prompt.is_shown, operator.not_, description="the question answered")


GESTURES: Final[Tuple[Tuple[str, Gesture], ...]] = (
    ("rename", rename),
    ("duplicate", duplicate),
    ("move", move),
    ("remove", remove),
)


def done(lines: Tuple[HistoryLine, ...]) -> Tuple[HistoryLine, ...]:
    """The lines of the entries done, from the one in force down, which leaves out those an undo set aside."""
    current = next(index for index, line in enumerate(lines) if line.current)
    return lines[current:]


def voice_segment_color(line: HistoryLine, name: str) -> Tuple[float, ...]:
    """The color of the piece of ``line`` naming the voice ``name``."""
    return next(segment.color for segment in line.segments if name in segment.words)


def position_color(line: HistoryLine, position: str) -> Tuple[float, ...]:
    """The color of the piece of ``line`` naming the voice by its ``position``."""
    return next(segment.color for segment in line.segments if segment.words.rstrip(POSITION_MARK) == position)


def naming_color(line: HistoryLine, voice: str, position: str) -> Tuple[float, ...]:
    """The color of the first piece of ``line`` naming the voice, by its name or by its ``position``."""
    return next(
        segment.color
        for segment in line.segments
        if voice in segment.words or segment.words.rstrip(POSITION_MARK) == position
    )


def one_more_than(count: int) -> Callable[[Tuple[HistoryLine, ...]], bool]:
    """Whether a reading of the lines done holds one more than ``count``."""
    return lambda lines: len(lines) == count + 1


def names_by_position_and_name(line: HistoryLine, voice: str, position: str) -> bool:
    words = [segment.words.rstrip(POSITION_MARK) for segment in line.segments]
    return position in words and any(voice in word for word in words)


def one_entry_per_gesture(gesture_name: str, gesture: Gesture, voice: str, position: str) -> Callable[[Screen], None]:
    """The step making ``gesture`` on ``voice``: one entry naming it in its kind's color, undone and redone at once."""

    def step(screen: Screen) -> None:
        voices = screen.sequencer.voices
        history = screen.sequencer.history
        before_names = voices.names()
        before = done(history.lines())
        kind = voices.kind_color(voice)

        gesture(screen, voice)

        after = screen.expect(
            lambda: done(history.lines()), lambda lines: len(lines) == len(before) + 1, description="one entry"
        )
        after_names = voices.names()
        assert after_names != before_names
        assert [line.segments for line in after[1:]] == [line.segments for line in before]
        assert naming_color(after[0], voice, position) == kind
        screen.press_shortcut(ShortcutId.UNDO)
        screen.expect(voices.names, before_names.__eq__, description=f"{gesture_name} undone")
        assert [line.segments for line in done(history.lines())] == [line.segments for line in before]
        screen.press_shortcut(ShortcutId.REDO)
        screen.expect(voices.names, after_names.__eq__, description=f"{gesture_name} redone")
        screen.press_shortcut(ShortcutId.UNDO)
        screen.expect(voices.names, before_names.__eq__, description=f"{gesture_name} undone again")

    step.__name__ = f"{gesture_name}_{voice.lower()}_is_one_entry"
    return step


def leave_as_opened(screen: Screen) -> None:
    """Exits a project every gesture of which was undone, which leaves at once."""
    screen.forgive_known_error(HOVER_RACE)
    assert screen.title() == titled(screen, ARRANGED_PROJECT.stem)

    screen.press_shortcut(ShortcutId.EXIT)

    assert screen.wait_for_exit()


def leave_letting_the_project_go(screen: Screen) -> None:
    screen.forgive_known_error(HOVER_RACE)
    prompt = screen.project.unsaved_prompt
    screen.press_shortcut(ShortcutId.EXIT)
    screen.expect(prompt.is_shown, bool, description="the question about the project")

    prompt.confirm()

    assert screen.wait_for_exit()


class TestEachVoiceGestureIsOneEntry:
    """Renaming, duplicating, moving and removing a sample or an instrument each make one entry.

    The entry names the voice in the color of its kind, and one undo and one redo take it back and
    forth.
    """

    def test_a_sample_and_an_instrument(self, screen: Screen) -> None:
        steps = [
            one_entry_per_gesture(name, gesture, voice, position)
            for voice, position in ((LINE, LINE_POSITION), (PAD, PAD_POSITION))
            for name, gesture in GESTURES
        ]

        screen.scenario(*steps, leave_as_opened).run()

    @pytest.mark.xfail(
        strict=True,
        raises=AssertionError,
        reason="bugs-and-todos § Bugs: the history lines of a renamed or a moved voice name it one way alone",
    )
    def test_every_line_names_the_voice_by_position_and_name(self, screen: Screen) -> None:
        history = screen.sequencer.history
        lines: List[HistoryLine] = []
        for gesture in (rename, move_down):
            before = len(done(history.lines()))
            gesture(screen, LINE)
            lines.append(
                screen.expect(lambda: done(history.lines()), one_more_than(before), description="its entry")[0]
            )
            screen.press_shortcut(ShortcutId.UNDO)
            screen.expect(screen.sequencer.voices.names, [LINE, BASS_VOICE, PAD].__eq__, description="undone")

        screen.forgive_known_error(HOVER_RACE)
        assert all(names_by_position_and_name(line, LINE, LINE_POSITION) for line in lines)

    def test_a_new_instrument_is_one_entry(self, screen: Screen) -> None:
        voices = screen.sequencer.voices
        history = screen.sequencer.history

        def add_one(screen: Screen) -> None:
            screen.tabs.bring_to_front(Tab.SEQUENCER)
            before = history.lines()

            voices.new_instrument()

            after = screen.expect(history.lines, lambda lines: len(lines) == len(before) + 1, description="one entry")
            assert len(voices.names()) == 4
            name = voices.names()[-1]
            assert voice_segment_color(after[0], name) == voices.kind_color(name)
            assert voices.kind_color(name) == voices.kind_color(PAD)

        def undo_takes_it_away(screen: Screen) -> None:
            screen.press_shortcut(ShortcutId.UNDO)

            screen.expect(voices.names, [LINE, BASS_VOICE, PAD].__eq__, description="the instrument gone")

        screen.scenario(add_one, undo_takes_it_away, leave_as_opened).run()


class TestAnEnvelopeDragIsOneEntry:
    """A drag across an instrument's envelope makes one entry naming the voice and the dimension; another, another.

    The entry names the instrument by its number, in the color of its kind.
    """

    def test_one_entry_per_dimension(self, screen: Screen) -> None:
        instruments = screen.reconstructions.instruments
        history = screen.sequencer.history
        lines: List[int] = []
        standing: List[str] = []

        def drag(feature: FeatureKey, end: float) -> None:
            graph = instruments.graph(ChannelName.PULSE1, feature)
            screen.hand.scroll_into_view(graph.plot)
            graph.drag_item(DRAGGED_ITEM, start=0.0, end=end)

        def drag_the_volume(screen: Screen) -> None:
            open_voice(screen, PAD)
            screen.expect(instruments.offers_audition, bool, description="the instrument open")
            lines.append(len(history.lines()))

            drag(FeatureKey.VOLUME, QUIET)

            after = screen.expect(history.lines, lambda found: len(found) == lines[0] + 1, description="one entry")
            assert position_color(after[0], PAD_POSITION) == screen.sequencer.voices.kind_color(PAD)
            assert VOLUME_LETTER in after[0].words.split()

        def drag_the_arpeggio(screen: Screen) -> None:
            standing.append(instruments.envelope(ChannelName.PULSE1, FeatureKey.ARPEGGIO))

            drag(FeatureKey.ARPEGGIO, ARPEGGIO_STEP)

            after = screen.expect(history.lines, lambda found: len(found) == lines[0] + 2, description="a second entry")
            assert ARPEGGIO_LETTER in after[0].words.split()

        def one_undo_takes_one_back(screen: Screen) -> None:
            screen.tabs.bring_to_front(Tab.SEQUENCER)

            history.undo()

            screen.expect(lambda: history.lines()[1].current, bool, description="one step back")
            assert instruments.envelope(ChannelName.PULSE1, FeatureKey.ARPEGGIO) == standing[0]

        screen.scenario(drag_the_volume, drag_the_arpeggio, one_undo_takes_one_back, leave_letting_the_project_go).run()
