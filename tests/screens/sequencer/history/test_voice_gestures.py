from typing import Callable, Final, List, Tuple

from sampletones_application.categories.hierarchy import Tab
from sampletones_application.utils.gui.shortcuts.ids import ShortcutId
from tests.screens.sequencer.history.cases import GESTURES, Gesture
from tests.screens.sequencer.history.constants import PAD_POSITION, POSITION_MARK
from tests.screens.sequencer.history.steps import pick, rename
from tests.suite.screens.screen import Screen
from tests.suite.screens.steps.reconstructions import titled
from tests.suite.screens.steps.sequencer import forgive_the_hover_race
from tests.suite.screens.views.history import HistoryLine
from tests.suite.screens.worlds.songs import ARRANGED_PROJECT, BASS_VOICE, LINE, PAD

LINE_POSITION: Final[str] = "00"


def move_down(screen: Screen, name: str) -> None:
    """Moves the voice ``name`` one place down."""
    pick(screen, name)
    screen.press_shortcut(ShortcutId.VOICES_MOVE_VOICE_DOWN)


def done(lines: Tuple[HistoryLine, ...]) -> Tuple[HistoryLine, ...]:
    """The lines of the entries done, from the one in force down, leaving out those an undo set aside."""
    current = next(index for index, line in enumerate(lines) if line.current)
    return lines[current:]


def voice_segment_color(line: HistoryLine, name: str) -> Tuple[float, ...]:
    """The color of the piece of ``line`` naming the voice ``name``."""
    return next(segment.color for segment in line.segments if name in segment.words)


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
    """Whether ``line`` names the voice both by its ``position`` and by its name."""
    words = [segment.words.rstrip(POSITION_MARK) for segment in line.segments]
    return position in words and any(voice in word for word in words)


def one_entry_per_gesture(gesture_name: str, gesture: Gesture, voice: str, position: str) -> Callable[[Screen], None]:
    """The step making ``gesture`` on ``voice``: one entry in its kind's color, undone and redone."""

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
    """Exits a project whose gestures were all undone; the window closes at once."""
    forgive_the_hover_race(screen)
    assert screen.title() == titled(screen, ARRANGED_PROJECT.stem)

    screen.press_shortcut(ShortcutId.EXIT)

    assert screen.wait_for_exit()


class TestEachVoiceGestureIsOneEntry:
    """Renaming, duplicating, moving and removing a sample or an instrument each make one entry.

    The entry names the voice in the color of its kind, and one undo and one redo take it back and forth.
    """

    def test_a_sample_and_an_instrument(self, screen: Screen) -> None:
        """Each of the four gestures on the sample and on the pad instrument adds one entry, and undo, redo and
        undo again move the voice list back and forth.
        """
        steps = [
            one_entry_per_gesture(name, gesture, voice, position)
            for voice, position in ((LINE, LINE_POSITION), (PAD, PAD_POSITION))
            for name, gesture in GESTURES
        ]

        screen.scenario(*steps, leave_as_opened).run()

    def test_every_line_names_the_voice_by_position_and_name(self, screen: Screen) -> None:
        """The entries of a renamed and of a moved sample each name it by its position and by its name."""
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

        forgive_the_hover_race(screen)
        assert all(names_by_position_and_name(line, LINE, LINE_POSITION) for line in lines)

    def test_a_new_instrument_is_one_entry(self, screen: Screen) -> None:
        """A new instrument adds one entry in the instrument color, and one undo removes the instrument."""
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
