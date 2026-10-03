import operator
from dataclasses import dataclass
from enum import StrEnum
from functools import partial
from typing import Callable, Final, List, Tuple

import pytest

from sampletones_application.utils.gui.shortcuts.ids import ShortcutId
from sampletones_core.constants.enums import ChannelName, FeatureKey
from tests.suite.screens.application import Startup
from tests.suite.screens.boundaries.dialogs import DialogKind
from tests.suite.screens.screen import Screen
from tests.suite.screens.steps.main import convert_alone, home_path
from tests.suite.screens.steps.reconstructions import (
    converted,
    edit_envelope,
    expect_open,
    load_from_the_browser,
    marked,
    raise_the_first_level,
    remove_from_the_browser,
    titled,
    voice_title,
)
from tests.suite.screens.steps.sequencer import double_click_voice, open_voice
from tests.suite.screens.vocabulary.dialogs import (
    CANCEL,
    CLOSE,
    CLOSE_MESSAGE,
    CLOSE_TITLE,
    DISCARD,
    EDIT_MESSAGE,
    EDIT_TITLE,
    EXIT_PROJECT_MESSAGE,
    EXIT_RECONSTRUCTION_MESSAGE,
    LOAD_MESSAGE,
    LOAD_TITLE,
    SAVE,
)
from tests.suite.screens.world import (
    BASS,
    LEAD,
    OPEN_RECONSTRUCTION,
    OTHER_RECONSTRUCTION,
    SONG,
    SONG_INSTRUMENT,
    SONG_SAMPLE,
)

SETTLING_FRAMES: Final[int] = 10
SAMPLE_ORDINAL: Final[int] = 0
FADING: Final[str] = "12 8 4"
EXIT_TITLE: Final[str] = "global.dialog.title.exit_confirmation"
EXIT: Final[str] = "global.dialog.label.exit"


class Door(StrEnum):
    """A gesture that puts the open document away, to replace it or to leave.

    A voice opens from a double-click on its row and from Edit on its row's menu.
    """

    BROWSER = "browser"
    MENU_OPEN = "menu_open"
    CLOSE = "close"
    VOICE = "voice"
    VOICE_MENU = "voice_menu"
    CONVERSION_LOAD = "conversion_load"
    EXIT = "exit"
    WINDOW_CLOSE = "window_close"


ASKING_DOORS: Final[Tuple[Door, ...]] = tuple(Door)


@dataclass(frozen=True)
class Question:
    """A question as the reader meets it: its title, its words and the answers it offers."""

    title: str
    words: str
    answers: Tuple[str, ...]


@dataclass(frozen=True)
class Standing:
    """What the screen shows of the open document, which a question taken back leaves as it was."""

    title: str
    file_line: str
    volume: str
    windows: Tuple[str, ...]
    dialogs: int


def question_at(screen: Screen, door: Door) -> Question:
    """The question ``door`` asks of a standalone reconstruction with unsaved changes, as the language file words it."""
    match door:
        case Door.BROWSER | Door.MENU_OPEN | Door.CONVERSION_LOAD:
            return Question(
                screen.words(LOAD_TITLE),
                screen.words(LOAD_MESSAGE),
                (screen.words(SAVE), screen.words(DISCARD), screen.words(CANCEL)),
            )
        case Door.CLOSE:
            return Question(
                screen.words(CLOSE_TITLE),
                screen.words(CLOSE_MESSAGE),
                (screen.words(SAVE), screen.words(CLOSE), screen.words(CANCEL)),
            )
        case Door.VOICE | Door.VOICE_MENU:
            return Question(
                screen.words(EDIT_TITLE),
                screen.words(EDIT_MESSAGE),
                (screen.words(SAVE), screen.words(DISCARD), screen.words(CANCEL)),
            )
        case Door.EXIT | Door.WINDOW_CLOSE:
            return Question(
                screen.words(EXIT_TITLE),
                screen.words(EXIT_RECONSTRUCTION_MESSAGE),
                (screen.words(SAVE), screen.words(EXIT), screen.words(CANCEL)),
            )


def knock(screen: Screen, door: Door, *, voice: str) -> None:
    """Makes the gesture ``door`` stands for; a door that loads loads Other.stn, the run's bass, or ``voice``."""
    match door:
        case Door.BROWSER:
            load_from_the_browser(screen, OTHER_RECONSTRUCTION)
        case Door.MENU_OPEN:
            screen.reconstructions.open_from_menu()
        case Door.CLOSE:
            screen.reconstructions.close_from_menu()
        case Door.VOICE:
            double_click_voice(screen, voice)
        case Door.VOICE_MENU:
            open_voice(screen, voice)
        case Door.CONVERSION_LOAD:
            convert_alone(screen, home_path(BASS), channel=ChannelName.PULSE1, replacing=[home_path(LEAD)])
            screen.main.converter.end_prompt.confirm()
            screen.expect(screen.main.converter.end_prompt.is_shown, operator.not_, description="the end answered")
        case Door.EXIT:
            screen.press_shortcut(ShortcutId.EXIT)
        case Door.WINDOW_CLOSE:
            screen.close_window()


def standing(screen: Screen) -> Standing:
    reconstructions = screen.reconstructions
    return Standing(
        title=screen.title(),
        file_line=reconstructions.file_line(),
        volume=reconstructions.instruments.envelope(ChannelName.PULSE1, FeatureKey.VOLUME),
        windows=tuple(window.alias for window in screen.shown_windows()),
        dialogs=len(screen.dialog_requests()),
    )


def asked(screen: Screen, door: Door) -> Question:
    prompt = screen.reconstructions.unsaved_prompt
    screen.expect(prompt.is_shown, bool, description=f"the question {door} asks")
    return Question(prompt.title(), prompt.words(), prompt.answers())


def asks_and_cancel_keeps_it(door: Door, *, voice: str) -> Callable[[Screen], None]:
    """The step knocking at ``door``, which asks its question, then taking it back, which leaves all standing."""

    def step(screen: Screen) -> None:
        prompt = screen.reconstructions.unsaved_prompt
        before = standing(screen)

        knock(screen, door, voice=voice)

        assert asked(screen, door) == question_at(screen, door)
        prompt.cancel()
        screen.expect(prompt.is_shown, operator.not_, description="the question taken back")
        screen.frames(SETTLING_FRAMES)
        assert screen.is_running()
        assert standing(screen) == before

    step.__name__ = f"{door.value}_asks_and_cancel_keeps_it"
    return step


def leave_letting_it_go(screen: Screen) -> None:
    """Exits, answering Exit to the question about the reconstruction."""
    prompt = screen.reconstructions.unsaved_prompt
    screen.press_shortcut(ShortcutId.EXIT)
    screen.expect(prompt.is_shown, bool, description="the question about the reconstruction")

    prompt.confirm()

    assert screen.wait_for_exit()


def leave_letting_the_project_go(screen: Screen) -> None:
    """Exits, answering Exit to the question about the project."""
    prompt = screen.project.unsaved_prompt
    screen.press_shortcut(ShortcutId.EXIT)
    screen.expect(prompt.is_shown, bool, description="the question about the project")

    prompt.confirm()

    assert screen.wait_for_exit()


def nothing_asked(screen: Screen) -> None:
    screen.frames(SETTLING_FRAMES)
    assert screen.shown_windows() == ()


def expect_title(screen: Screen, title: str) -> None:
    screen.expect(screen.title, title.__eq__, description=f"the title reading '{title}'")


class TestAnEditedReconstructionAtEveryDoor:
    """Every door asks about an edited reconstruction in its own words, and Cancel leaves everything standing."""

    @pytest.fixture
    def startup(self) -> Startup:
        return Startup(reconstruction=OPEN_RECONSTRUCTION, project=SONG)

    def test_each_door_asks_its_question(self, screen: Screen) -> None:
        def edit_it(screen: Screen) -> None:
            expect_open(screen, OPEN_RECONSTRUCTION)

            raise_the_first_level(
                screen,
                ChannelName.PULSE1,
                title=titled(screen, SONG.stem, marked(OPEN_RECONSTRUCTION.name, unsaved=True)),
            )

        screen.scenario(
            edit_it,
            *(asks_and_cancel_keeps_it(door, voice=SONG_SAMPLE) for door in ASKING_DOORS),
            leave_letting_it_go,
        ).run()


class TestAReconstructionWhoseFileWasRemovedAtEveryDoor:
    """Every door asks about a reconstruction whose file was removed, as it asks about an edited one."""

    @pytest.fixture
    def startup(self) -> Startup:
        return Startup(reconstruction=OPEN_RECONSTRUCTION, project=SONG)

    def test_each_door_asks_its_question(self, screen: Screen) -> None:
        def remove_its_file(screen: Screen) -> None:
            expect_open(screen, OPEN_RECONSTRUCTION)

            remove_from_the_browser(screen, OPEN_RECONSTRUCTION)

            expect_title(screen, titled(screen, SONG.stem, marked(OPEN_RECONSTRUCTION.name, unsaved=True)))

        screen.scenario(
            remove_its_file,
            *(asks_and_cancel_keeps_it(door, voice=SONG_SAMPLE) for door in ASKING_DOORS),
            leave_letting_it_go,
        ).run()


class TestAnEditedSampleAtEveryDoor:
    """An edited sample of the project is put away without a question, its edits kept in the project.

    The exit asks about the project alone.
    """

    @pytest.fixture
    def startup(self) -> Startup:
        return Startup(reconstruction=None, project=SONG)

    def test_no_door_asks_and_the_exit_asks_about_the_project(self, screen: Screen) -> None:
        reconstructions = screen.reconstructions
        edit: List[str] = []
        sample_open = partial(voice_title, screen, SONG.stem, SAMPLE_ORDINAL, SONG_SAMPLE, unsaved=True)

        def open_the_sample(screen: Screen) -> None:
            open_voice(screen, SONG_SAMPLE)
            expect_title(screen, sample_open())
            assert reconstructions.instruments.envelope(ChannelName.PULSE1, FeatureKey.VOLUME) == edit[0]

        def edit_the_sample(screen: Screen) -> None:
            open_voice(screen, SONG_SAMPLE)
            expect_title(screen, voice_title(screen, SONG.stem, SAMPLE_ORDINAL, SONG_SAMPLE, unsaved=False))

            edit.append(raise_the_first_level(screen, ChannelName.PULSE1, title=sample_open()))

        def the_browser_loads_at_once(screen: Screen) -> None:
            knock(screen, Door.BROWSER, voice=SONG_SAMPLE)

            expect_title(screen, titled(screen, marked(SONG.stem, unsaved=True), OTHER_RECONSTRUCTION.name))
            nothing_asked(screen)
            open_the_sample(screen)

        def the_menu_asks_for_a_file_at_once(screen: Screen) -> None:
            screen.answer_next_dialog(DialogKind.OPEN, OTHER_RECONSTRUCTION)

            knock(screen, Door.MENU_OPEN, voice=SONG_SAMPLE)

            expect_title(screen, titled(screen, marked(SONG.stem, unsaved=True), OTHER_RECONSTRUCTION.name))
            nothing_asked(screen)
            open_the_sample(screen)

        def another_voice_opens_at_once(screen: Screen) -> None:
            knock(screen, Door.VOICE_MENU, voice=SONG_INSTRUMENT)

            screen.expect(reconstructions.instruments.offers_audition, bool, description="the instrument open")
            assert screen.title() == titled(screen, marked(SONG.stem, unsaved=True))
            nothing_asked(screen)
            open_the_sample(screen)

        def close_closes_at_once(screen: Screen) -> None:
            knock(screen, Door.CLOSE, voice=SONG_SAMPLE)

            expect_title(screen, titled(screen, marked(SONG.stem, unsaved=True)))
            assert reconstructions.file_line() == ""
            nothing_asked(screen)
            open_the_sample(screen)

        def the_conversion_loads_at_once(screen: Screen) -> None:
            knock(screen, Door.CONVERSION_LOAD, voice=SONG_SAMPLE)

            expect_title(screen, titled(screen, marked(SONG.stem, unsaved=True), converted(home_path(BASS)).name))
            nothing_asked(screen)
            open_the_sample(screen)

        def leaving_asks_about_the_project(door: Door) -> Callable[[Screen], None]:
            def step(screen: Screen) -> None:
                prompt = screen.project.unsaved_prompt

                knock(screen, door, voice=SONG_SAMPLE)

                screen.expect(prompt.is_shown, bool, description="the question about the project")
                assert prompt.words() == screen.words(EXIT_PROJECT_MESSAGE)
                assert not reconstructions.unsaved_prompt.is_shown()
                prompt.cancel()
                screen.expect(prompt.is_shown, operator.not_, description="the question taken back")
                screen.frames(SETTLING_FRAMES)
                assert screen.title() == sample_open()

            step.__name__ = f"{door.value}_asks_about_the_project"
            return step

        screen.scenario(
            edit_the_sample,
            the_browser_loads_at_once,
            the_menu_asks_for_a_file_at_once,
            another_voice_opens_at_once,
            close_closes_at_once,
            the_conversion_loads_at_once,
            leaving_asks_about_the_project(Door.EXIT),
            leaving_asks_about_the_project(Door.WINDOW_CLOSE),
            leave_letting_the_project_go,
        ).run()


class TestAnInstrumentAtEveryDoor:
    """An instrument is put away without a question, Close has nothing to close, and the exit asks about the project."""

    @pytest.fixture
    def startup(self) -> Startup:
        return Startup(reconstruction=None, project=SONG)

    def test_no_door_asks_and_close_stands_aside(self, screen: Screen) -> None:
        reconstructions = screen.reconstructions
        edited = titled(screen, marked(SONG.stem, unsaved=True))

        def open_the_instrument(screen: Screen) -> None:
            open_voice(screen, SONG_INSTRUMENT)
            screen.expect(reconstructions.instruments.offers_audition, bool, description="the instrument open")
            screen.expect(
                lambda: reconstructions.instruments.envelope(ChannelName.PULSE1, FeatureKey.VOLUME),
                FADING.__eq__,
                description="its edit drawn",
            )

        def edit_the_instrument(screen: Screen) -> None:
            open_voice(screen, SONG_INSTRUMENT)
            screen.expect(reconstructions.instruments.offers_audition, bool, description="the instrument open")

            edit_envelope(screen, channel=ChannelName.PULSE1, feature=FeatureKey.VOLUME, sequence=FADING, title=edited)

        def the_browser_loads_at_once(screen: Screen) -> None:
            knock(screen, Door.BROWSER, voice=SONG_SAMPLE)

            expect_title(screen, titled(screen, marked(SONG.stem, unsaved=True), OTHER_RECONSTRUCTION.name))
            assert not reconstructions.instruments.offers_audition()
            nothing_asked(screen)
            open_the_instrument(screen)

        def the_menu_asks_for_a_file_at_once(screen: Screen) -> None:
            screen.answer_next_dialog(DialogKind.OPEN, OTHER_RECONSTRUCTION)

            knock(screen, Door.MENU_OPEN, voice=SONG_SAMPLE)

            expect_title(screen, titled(screen, marked(SONG.stem, unsaved=True), OTHER_RECONSTRUCTION.name))
            nothing_asked(screen)
            open_the_instrument(screen)

        def a_sample_opens_at_once(screen: Screen) -> None:
            knock(screen, Door.VOICE_MENU, voice=SONG_SAMPLE)

            expect_title(screen, voice_title(screen, SONG.stem, SAMPLE_ORDINAL, SONG_SAMPLE, unsaved=True))
            assert not reconstructions.instruments.offers_audition()
            nothing_asked(screen)
            open_the_instrument(screen)

        def close_has_nothing_to_close(screen: Screen) -> None:
            assert not reconstructions.can_close()

            screen.press_shortcut(ShortcutId.CLOSE_RECONSTRUCTION)

            nothing_asked(screen)
            assert reconstructions.instruments.offers_audition()
            assert reconstructions.instruments.envelope(ChannelName.PULSE1, FeatureKey.VOLUME) == FADING
            assert screen.title() == edited

        def the_conversion_loads_at_once(screen: Screen) -> None:
            knock(screen, Door.CONVERSION_LOAD, voice=SONG_SAMPLE)

            expect_title(screen, titled(screen, marked(SONG.stem, unsaved=True), converted(home_path(BASS)).name))
            nothing_asked(screen)
            open_the_instrument(screen)

        def leaving_asks_about_the_project(door: Door) -> Callable[[Screen], None]:
            def step(screen: Screen) -> None:
                prompt = screen.project.unsaved_prompt

                knock(screen, door, voice=SONG_SAMPLE)

                screen.expect(prompt.is_shown, bool, description="the question about the project")
                assert prompt.words() == screen.words(EXIT_PROJECT_MESSAGE)
                prompt.cancel()
                screen.expect(prompt.is_shown, operator.not_, description="the question taken back")
                screen.frames(SETTLING_FRAMES)
                assert reconstructions.instruments.offers_audition()

            step.__name__ = f"{door.value}_asks_about_the_project"
            return step

        screen.scenario(
            edit_the_instrument,
            the_browser_loads_at_once,
            the_menu_asks_for_a_file_at_once,
            a_sample_opens_at_once,
            close_has_nothing_to_close,
            the_conversion_loads_at_once,
            leaving_asks_about_the_project(Door.EXIT),
            leaving_asks_about_the_project(Door.WINDOW_CLOSE),
            leave_letting_the_project_go,
        ).run()


class TestASavedReconstructionAtEveryDoor:
    """A reconstruction with nothing unsaved is put away at every door without a question, and leaving leaves."""

    @pytest.fixture
    def startup(self) -> Startup:
        return Startup(reconstruction=OPEN_RECONSTRUCTION, project=SONG)

    def test_no_door_asks(self, screen: Screen) -> None:
        def the_browser_loads_at_once(screen: Screen) -> None:
            expect_open(screen, OPEN_RECONSTRUCTION)

            knock(screen, Door.BROWSER, voice=SONG_SAMPLE)

            expect_title(screen, titled(screen, SONG.stem, OTHER_RECONSTRUCTION.name))
            nothing_asked(screen)

        def the_menu_asks_for_a_file_at_once(screen: Screen) -> None:
            screen.answer_next_dialog(DialogKind.OPEN, OPEN_RECONSTRUCTION)

            knock(screen, Door.MENU_OPEN, voice=SONG_SAMPLE)

            expect_title(screen, titled(screen, SONG.stem, OPEN_RECONSTRUCTION.name))
            nothing_asked(screen)

        def the_conversion_loads_at_once(screen: Screen) -> None:
            knock(screen, Door.CONVERSION_LOAD, voice=SONG_SAMPLE)

            expect_title(screen, titled(screen, SONG.stem, converted(home_path(BASS)).name))
            nothing_asked(screen)

        def a_voice_opens_at_once(screen: Screen) -> None:
            knock(screen, Door.VOICE_MENU, voice=SONG_SAMPLE)

            expect_title(screen, voice_title(screen, SONG.stem, SAMPLE_ORDINAL, SONG_SAMPLE, unsaved=False))
            nothing_asked(screen)

        def close_closes_at_once(screen: Screen) -> None:
            load_from_the_browser(screen, OPEN_RECONSTRUCTION)
            expect_open(screen, OPEN_RECONSTRUCTION)

            knock(screen, Door.CLOSE, voice=SONG_SAMPLE)

            expect_title(screen, titled(screen, SONG.stem))
            nothing_asked(screen)

        def the_window_closes_at_once(screen: Screen) -> None:
            load_from_the_browser(screen, OPEN_RECONSTRUCTION)
            expect_open(screen, OPEN_RECONSTRUCTION)

            knock(screen, Door.WINDOW_CLOSE, voice=SONG_SAMPLE)

            assert screen.wait_for_exit()

        screen.scenario(
            the_browser_loads_at_once,
            the_menu_asks_for_a_file_at_once,
            the_conversion_loads_at_once,
            a_voice_opens_at_once,
            close_closes_at_once,
            the_window_closes_at_once,
        ).run()

    def test_exit_leaves_at_once(self, screen: Screen) -> None:
        expect_open(screen, OPEN_RECONSTRUCTION)

        knock(screen, Door.EXIT, voice=SONG_SAMPLE)

        assert screen.wait_for_exit()


class TestNothingOpenAtEveryDoor:
    """With nothing open, every door that loads loads at once, and Close has nothing to close."""

    @pytest.fixture
    def startup(self) -> Startup:
        return Startup(reconstruction=None, project=SONG)

    def test_each_door_loads_at_once(self, screen: Screen) -> None:
        reconstructions = screen.reconstructions
        empty = titled(screen, SONG.stem)

        def close_it_again(screen: Screen) -> None:
            reconstructions.close_from_menu()
            expect_title(screen, empty)

        def close_has_nothing_to_close(screen: Screen) -> None:
            assert not reconstructions.can_close()

            screen.press_shortcut(ShortcutId.CLOSE_RECONSTRUCTION)

            nothing_asked(screen)
            assert screen.title() == empty

        def the_browser_loads_at_once(screen: Screen) -> None:
            knock(screen, Door.BROWSER, voice=SONG_SAMPLE)

            expect_title(screen, titled(screen, SONG.stem, OTHER_RECONSTRUCTION.name))
            nothing_asked(screen)
            close_it_again(screen)

        def the_menu_asks_for_a_file_at_once(screen: Screen) -> None:
            screen.answer_next_dialog(DialogKind.OPEN, OTHER_RECONSTRUCTION)

            knock(screen, Door.MENU_OPEN, voice=SONG_SAMPLE)

            expect_title(screen, titled(screen, SONG.stem, OTHER_RECONSTRUCTION.name))
            nothing_asked(screen)
            close_it_again(screen)

        def a_voice_opens_at_once(screen: Screen) -> None:
            knock(screen, Door.VOICE_MENU, voice=SONG_SAMPLE)

            expect_title(screen, voice_title(screen, SONG.stem, SAMPLE_ORDINAL, SONG_SAMPLE, unsaved=False))
            nothing_asked(screen)
            close_it_again(screen)

        def the_conversion_loads_at_once(screen: Screen) -> None:
            knock(screen, Door.CONVERSION_LOAD, voice=SONG_SAMPLE)

            expect_title(screen, titled(screen, SONG.stem, converted(home_path(BASS)).name))
            nothing_asked(screen)

        screen.scenario(
            close_has_nothing_to_close,
            the_browser_loads_at_once,
            the_menu_asks_for_a_file_at_once,
            a_voice_opens_at_once,
            the_conversion_loads_at_once,
        ).run()

    def test_the_window_closes_at_once(self, screen: Screen) -> None:
        screen.expect(screen.title, titled(screen, SONG.stem).__eq__, description="the song open")

        knock(screen, Door.WINDOW_CLOSE, voice=SONG_SAMPLE)

        assert screen.wait_for_exit()
