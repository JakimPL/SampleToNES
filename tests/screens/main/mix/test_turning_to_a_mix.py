import operator
from functools import partial
from pathlib import Path
from typing import Final, List

import pytest

from sampletones_application.constants.conversion import MAX_STEM_SOURCES
from sampletones_application.constants.output import OutputKind
from tests.suite.screens.screen import Screen
from tests.suite.screens.seeds.recordings import Recording
from tests.suite.screens.steps.main import gather, home_path
from tests.suite.screens.vocabulary.converter import REMOVE_RECORDING
from tests.suite.screens.worlds.home import World
from tests.suite.screens.worlds.recordings import lived_in_world

GATHERED: Final[int] = MAX_STEM_SOURCES + 2
SECONDS: Final[float] = 2.0
FREQUENCY: Final[float] = 220.0
NAMES_CLICKED: Final[int] = 4
COUNT_LINE: Final[str] = "main.converter.template.stem_selection_limit"

MOVES: Final[List[str]] = [
    "main.converter.label.context_move_up",
    "main.converter.label.context_move_down",
    "main.converter.label.context_join_above",
    "main.converter.label.context_join_below",
    "main.converter.label.context_isolate",
]


def recording(index: int) -> Path:
    """The home path of the gathered recording numbered ``index``."""
    return home_path(f"voice{index:02d}.wav")


def recordings(count: int) -> List[Path]:
    """The home paths of the first ``count`` gathered recordings."""
    return [recording(index) for index in range(count)]


@pytest.fixture
def world() -> World:
    """A lived-in home holding two more recordings than a mix has room for."""
    files = tuple(Recording(destination=path, seconds=SECONDS, frequency=FREQUENCY) for path in recordings(GATHERED))
    return World(state=lived_in_world().state, application_config=None, config=None, files=files)


def count_line(screen: Screen, picked: int, total: int) -> str:
    """The line the mix question shows for ``picked`` recordings ticked out of ``total``."""
    return screen.words(COUNT_LINE).format(picked=picked, total=total, room=MAX_STEM_SOURCES)


class TestTurningToAMixPastItsRoom:
    """Turning to a mix with more recordings gathered than a mix holds asks which to take, with a full
    pick ticked.
    """

    def test_the_question_ticks_a_full_pick_and_cancel_leaves_everything(self, screen: Screen) -> None:
        """The question ticks the first recordings up to the room of a mix; Cancel keeps the list and the
        per-recording switch, and turning to a mix again asks again.
        """
        main = screen.main
        question = main.converter.mix_question
        paths = recordings(GATHERED)

        def turn_to_a_mix(screen: Screen) -> None:
            gather(screen, *paths)

            main.choose_output(OutputKind.MIXED)

            screen.expect(question.is_shown, bool, description="the question")
            picked, past = paths[:MAX_STEM_SOURCES], paths[MAX_STEM_SOURCES:]
            assert all(question.is_ticked(path) for path in picked)
            assert not any(question.is_ticked(path) or question.is_live(path) for path in past)
            assert question.count_line() == count_line(screen, MAX_STEM_SOURCES, GATHERED)

        def cancel_leaves_the_list_and_the_switch(screen: Screen) -> None:
            question.cancel()

            screen.expect(question.is_shown, operator.not_, description="the question gone")
            assert main.output() is OutputKind.PER_RECORDING
            assert main.converter.list.rows() == [main.converter.list.row(path) for path in paths]

        def asking_again_asks_again(screen: Screen) -> None:
            main.choose_output(OutputKind.MIXED)

            screen.expect(question.is_shown, bool, description="the question again")
            question.cancel()
            screen.expect(question.is_shown, operator.not_, description="the question gone again")

        screen.scenario(turn_to_a_mix, cancel_leaves_the_list_and_the_switch, asking_again_asks_again).run()

    def test_a_full_pick_swaps_one_for_one_and_add_waits_for_a_pick(self, screen: Screen) -> None:
        """With a full pick, letting one go makes the next recording live for ticking; Add answers once at
        least one recording is picked and then makes the mix.
        """
        main = screen.main
        question = main.converter.mix_question
        paths = recordings(GATHERED)
        ninth = paths[MAX_STEM_SOURCES]

        def open_the_question(screen: Screen) -> None:
            gather(screen, *paths)
            main.choose_output(OutputKind.MIXED)
            screen.expect(question.is_shown, bool, description="the question")

        def letting_one_go_makes_the_ninth_live(screen: Screen) -> None:
            assert not question.is_live(ninth)

            question.tick(paths[0])

            screen.expect(partial(question.is_live, ninth), bool, description="the ninth live")
            assert question.count_line() == count_line(screen, MAX_STEM_SOURCES - 1, GATHERED)
            question.tick(ninth)
            screen.expect(partial(question.is_ticked, ninth), bool, description="the ninth picked")
            assert question.count_line() == count_line(screen, MAX_STEM_SOURCES, GATHERED)
            assert not question.is_live(paths[0])

        def add_waits_until_something_is_picked(screen: Screen) -> None:
            for path in paths[1 : MAX_STEM_SOURCES + 1]:
                question.tick(path)
            screen.expect(question.can_add, operator.not_, description="Add waiting")
            assert question.count_line() == count_line(screen, 0, GATHERED)

            question.tick(paths[0])

            screen.expect(question.can_add, bool, description="Add answering")

        def add_makes_the_mix(screen: Screen) -> None:
            question.add()

            screen.expect(question.is_shown, operator.not_, description="the question gone")
            screen.expect(main.output, OutputKind.MIXED.__eq__, description="the switch on a mix")

        screen.scenario(
            open_the_question,
            letting_one_go_makes_the_ninth_live,
            add_waits_until_something_is_picked,
            add_makes_the_mix,
        ).run()

    def test_a_double_click_sounds_a_row_and_names_leave_no_highlight(self, screen: Screen) -> None:
        """A double-click on a name plays that recording, and clicking names leaves the ticks and highlights
        as they were.
        """
        main = screen.main
        question = main.converter.mix_question
        paths = recordings(GATHERED)

        def open_the_question(screen: Screen) -> None:
            gather(screen, *paths)
            main.choose_output(OutputKind.MIXED)
            screen.expect(question.is_shown, bool, description="the question")

        def a_double_click_sounds_it(screen: Screen) -> None:
            heard = screen.sound_heard()
            screen.hand.double_click(question.name(paths[0]))

            screen.expect(screen.sound_heard, heard.__lt__, description="the recording heard")

        def names_clicked_leave_no_highlight(screen: Screen) -> None:
            before = [question.is_ticked(path) for path in paths]
            for path in paths[1 : 1 + NAMES_CLICKED]:
                screen.hand.scroll_into_view(question.name(path))
                screen.hand.click(question.name(path))

            assert not any(question.is_highlighted(path) for path in paths)
            assert [question.is_ticked(path) for path in paths] == before
            question.cancel()
            screen.expect(question.is_shown, operator.not_, description="the question gone")

        screen.scenario(open_the_question, a_double_click_sounds_it, names_clicked_leave_no_highlight).run()


class TestAMixOfOneAndOfTwo:
    """A mix of one draws no level band and offers no moves; a second recording brings the bands, and
    one per recording takes them away.

    One recording is gathered and the switch turned to a mix. Its right-click menu lists Remove and no
    moves. A second recording brings the level bands; turning back to one per recording removes them.
    """

    def test_bands_come_with_the_second_recording_and_go_with_one_per_recording(self, screen: Screen) -> None:
        main = screen.main
        listing = main.converter.list
        menu = screen.context_menu
        first, second = recordings(2)

        def a_mix_of_one(screen: Screen) -> None:
            gather(screen, first)
            main.choose_output(OutputKind.MIXED)
            screen.expect(main.output, OutputKind.MIXED.__eq__, description="the switch on a mix")

            assert not listing.has_levels()

        def its_menu_offers_removal_and_no_moves(screen: Screen) -> None:
            screen.hand.right_click(listing.row(first))
            screen.expect(menu.is_shown, bool, description="the menu")

            labels = menu.labels()

            menu.dismiss()
            screen.expect(menu.is_shown, operator.not_, description="the menu put away")
            assert screen.words(REMOVE_RECORDING) in labels
            assert not set(labels) & {screen.words(move) for move in MOVES}

        def the_second_brings_the_bands(screen: Screen) -> None:
            gather(screen, second)

            screen.expect(listing.has_levels, bool, description="the level bands")

        def one_per_recording_takes_them_away(screen: Screen) -> None:
            main.choose_output(OutputKind.PER_RECORDING)

            screen.expect(listing.has_levels, operator.not_, description="the bands gone")
            assert listing.rows() == [listing.row(first), listing.row(second)]

        screen.scenario(
            a_mix_of_one,
            its_menu_offers_removal_and_no_moves,
            the_second_brings_the_bands,
            one_per_recording_takes_them_away,
        ).run()
