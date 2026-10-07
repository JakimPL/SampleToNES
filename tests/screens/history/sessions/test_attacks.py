import operator
from typing import Final, List

from sampletones_application.categories.hierarchy import Tab
from sampletones_application.utils.gui.shortcuts.ids import ShortcutId
from sampletones_application.view_model.sequencer.subcolumn import SubColumn
from sampletones_core.constants.enums import ChannelName, FeatureKey
from tests.screens.history.constants import EVERY_STEP, LEAD
from tests.screens.history.steps import (
    expect_lines,
    expect_reading,
    history_count,
    press_on_the_sequencer,
    volume_fields,
)
from tests.suite.screens.holds.regeneration import RegenerationHold
from tests.suite.screens.screen import Screen
from tests.suite.screens.steps.sequencer import leave_letting_the_project_go, open_voice

TEMPO: Final[int] = 111
LONG_PATTERNS: Final[int] = 64
TRACKER_ROW: Final[int] = 5
TRACKER_VOLUME: Final[str] = "3"
SECOND_VOLUME: Final[str] = "4"
LEAD_VOLUME: Final[str] = "2 1"
CHANNELS: Final = (ChannelName.PULSE1,)


def tracker_volume(screen: Screen) -> str:
    return screen.sequencer.tracker.label(TRACKER_ROW, ChannelName.PULSE1, SubColumn.VOLUME)


def type_a_tracker_volume(
    screen: Screen,
    volume: str,
) -> None:
    lines = history_count(screen)
    screen.tabs.bring_to_front(Tab.SEQUENCER)
    screen.sequencer.tracker.click(TRACKER_ROW, ChannelName.PULSE1, SubColumn.VOLUME)
    screen.hand.type_text(volume)
    screen.expect(lambda: tracker_volume(screen), volume.__eq__, description=f"the volume {volume}")
    screen.expect(
        lambda: history_count(screen) != lines or screen.sequencer.history.lines()[0].current,
        bool,
        description="the line in force",
    )


class TestUndoAndRedoPastEitherEnd:
    """Undo pressed again and again at the start and Redo again and again at the end change nothing more.

    Twenty undos at the opened project leave the tempo and the card as they were. Retyping the tempo adds a
    line, which witnesses the keys; one undo takes it back and twenty redos bring it back once.
    """

    def test_the_ends_hold(self, screen: Screen) -> None:
        module = screen.sequencer.module
        tempos: List[int] = []
        lines: List[int] = []

        def twenty_undos_at_the_start(screen: Screen) -> None:
            screen.tabs.bring_to_front(Tab.SEQUENCER)
            tempos.append(module.tempo())
            lines.append(history_count(screen))

            for _ in range(EVERY_STEP):
                screen.press_shortcut(ShortcutId.UNDO)

            assert module.tempo() == tempos[0]
            assert history_count(screen) == lines[0]

        def the_keys_act_inside_the_stack(screen: Screen) -> None:
            module.retype_tempo(TEMPO)
            expect_lines(screen, lines[0] + 1)
            press_on_the_sequencer(screen, ShortcutId.UNDO)
            screen.expect(module.tempo, tempos[0].__eq__, description="the tempo as it stood")

            for _ in range(EVERY_STEP):
                screen.press_shortcut(ShortcutId.REDO)

            screen.expect(module.tempo, TEMPO.__eq__, description="the tempo as typed")
            assert history_count(screen) == lines[0] + 1

        screen.scenario(twenty_undos_at_the_start, the_keys_act_inside_the_stack, leave_letting_the_project_go).run()


class TestAnUndoWhileTheSongPlays:
    """An edit undone while the song plays takes the cell back and stops the song, as opening a project does.

    The patterns are lengthened so the song outlasts the steps, a tracker volume is typed and the song
    started. Undo takes the cell back and the song stops, since a restore rebuilds the Sequencer the way
    loading a project does; Play then starts the song again, which witnesses the stop.
    """

    def test_the_cell_comes_back(self, screen: Screen) -> None:
        playback = screen.sequencer.playback
        standing: List[str] = []

        def edit_and_play(screen: Screen) -> None:
            screen.tabs.bring_to_front(Tab.SEQUENCER)
            screen.sequencer.module.retype_rows(LONG_PATTERNS)
            screen.expect(screen.sequencer.module.rows, LONG_PATTERNS.__eq__, description="the long patterns")
            standing.append(tracker_volume(screen))
            type_a_tracker_volume(screen, TRACKER_VOLUME)

            playback.play()

            screen.expect(playback.can_stop, bool, description="the song playing")

        def undo_while_playing(screen: Screen) -> None:
            press_on_the_sequencer(screen, ShortcutId.UNDO)

            expect_reading(screen, lambda: tracker_volume(screen), standing[0], "the cell as it stood")
            screen.expect(playback.can_stop, operator.not_, description="the song stopped")

        def play_again_and_leave(screen: Screen) -> None:
            playback.play()
            screen.expect(playback.can_stop, bool, description="the song playing again")
            playback.stop()
            screen.expect(playback.can_stop, operator.not_, description="the song stopped")

            leave_letting_the_project_go(screen)

        screen.scenario(edit_and_play, undo_while_playing, play_again_and_leave).run()


class TestTheExitAfterUndos:
    """The exit asks nothing once undos return to the opened project, and asks while an edit still stands.

    One tracker edit undone leaves the project clean, so the exit closes at once. Two edits with one undone
    leave it changed, so the exit asks first.
    """

    def test_back_at_the_file_the_exit_asks_nothing(self, screen: Screen) -> None:
        def edit_and_undo(screen: Screen) -> None:
            type_a_tracker_volume(screen, TRACKER_VOLUME)

            press_on_the_sequencer(screen, ShortcutId.UNDO)

            screen.expect(
                lambda: screen.sequencer.history.lines()[-1].current, bool, description="the opened line in force"
            )

        def leave(screen: Screen) -> None:
            screen.press_shortcut(ShortcutId.EXIT)

            assert screen.wait_for_exit()

        screen.scenario(edit_and_undo, leave).run()

    def test_an_edit_still_standing_is_asked_about(self, screen: Screen) -> None:
        def two_edits_and_one_undo(screen: Screen) -> None:
            type_a_tracker_volume(screen, TRACKER_VOLUME)
            screen.sequencer.module.retype_tempo(TEMPO)
            screen.expect(screen.sequencer.module.tempo, TEMPO.__eq__, description="the tempo as typed")

            press_on_the_sequencer(screen, ShortcutId.UNDO)

            screen.expect(lambda: tracker_volume(screen), TRACKER_VOLUME.__eq__, description="the first edit standing")

        screen.scenario(two_edits_and_one_undo, leave_letting_the_project_go).run()


class TestAJumpWhileAnEditIsOnItsWay:
    """A click on the oldest line while an edit is still being rebuilt waits for it, then lands at the opened project.

    Lead opens with its rebuilds held and a volume is typed. The oldest line is clicked while the rebuild
    waits, and the card stays as it was. Once the rebuild goes, the edit lands as a line of its own and the
    jump puts the opened project back; Redo brings the typed values back.
    """

    def test_the_jump_comes_after_the_edit(
        self,
        screen: Screen,
        regeneration_hold: RegenerationHold,
    ) -> None:
        history = screen.sequencer.history
        standing: List[object] = []
        lines: List[int] = []

        def type_while_held(screen: Screen) -> None:
            open_voice(screen, LEAD)
            screen.expect(screen.tabs.front, Tab.RECONSTRUCTIONS.__eq__, description="Lead open")
            standing.append(volume_fields(screen, CHANNELS))
            lines.append(history_count(screen))

            screen.reconstructions.instruments.type_envelope(ChannelName.PULSE1, FeatureKey.VOLUME, LEAD_VOLUME)

            screen.expect(regeneration_hold.waiting, bool, description="the rebuild held")

        def click_the_oldest_line(screen: Screen) -> None:
            screen.tabs.bring_to_front(Tab.SEQUENCER)

            history.jump_to(history_count(screen) - 1)

            assert history_count(screen) == lines[0]

        def the_edit_lands_and_the_jump_follows(screen: Screen) -> None:
            regeneration_hold.release()

            expect_lines(screen, lines[0] + 1)
            expect_reading(screen, lambda: volume_fields(screen, CHANNELS), standing[0], "the volume as it stood")
            assert history.lines()[-1].current

        def redo_brings_the_edit_back(screen: Screen) -> None:
            press_on_the_sequencer(screen, ShortcutId.REDO)

            screen.expect(
                lambda: volume_fields(screen, CHANNELS)[ChannelName.PULSE1].split()[:2] == LEAD_VOLUME.split(),
                bool,
                description="the volume as typed",
            )

        screen.scenario(
            type_while_held,
            click_the_oldest_line,
            the_edit_lands_and_the_jump_follows,
            redo_brings_the_edit_back,
            leave_letting_the_project_go,
        ).run()
