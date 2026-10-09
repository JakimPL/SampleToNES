import operator
from typing import Callable, Final

import pytest

from automation.application.startup import Startup
from automation.screen import Screen
from automation.steps.reconstructions import (
    expect_open,
    marked,
    raise_the_first_level,
    remove_from_the_browser,
    titled,
)
from automation.vocabulary.dialogs import (
    CANCEL,
    CLOSE,
    CLOSE_MESSAGE,
    CLOSE_TITLE,
    DISCARD,
    EDIT_MESSAGE,
    EDIT_TITLE,
    EXIT_RECONSTRUCTION_MESSAGE,
    LOAD_MESSAGE,
    LOAD_TITLE,
    SAVE,
)
from sampletones_application.utils.gui.shortcuts.ids import ShortcutId
from sampletones_core.constants.enums import ChannelName, FeatureKey
from tests.screens.prompts.every_door.cases import ASKING_DOORS, Door, Question, Standing
from tests.screens.prompts.every_door.constants import EXIT, SETTLING_FRAMES
from tests.screens.prompts.every_door.steps import expect_title, knock
from tests.suite.screens.worlds.recordings import OPEN_RECONSTRUCTION, SONG, SONG_SAMPLE

EXIT_TITLE: Final[str] = "global.dialog.title.exit_confirmation"


def question_at(screen: Screen, door: Door) -> Question:
    """The question ``door`` asks about a standalone reconstruction with unsaved changes, in the words of the
    language file.
    """
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


def standing(screen: Screen) -> Standing:
    """What the screen shows of the open reconstruction right now."""
    reconstructions = screen.reconstructions
    return Standing(
        title=screen.title(),
        file_line=reconstructions.file_line(),
        volume=reconstructions.instruments.envelope(ChannelName.PULSE1, FeatureKey.VOLUME),
        windows=tuple(window.alias for window in screen.shown_windows()),
        dialogs=len(screen.dialog_requests()),
    )


def asked(screen: Screen, door: Door) -> Question:
    """Waits for the question about the reconstruction and returns it as the screen shows it."""
    prompt = screen.reconstructions.unsaved_prompt
    screen.expect(prompt.is_shown, bool, description=f"the question {door} asks")
    return Question(prompt.title(), prompt.words(), prompt.answers())


def asks_and_cancel_keeps_it(door: Door, *, voice: str) -> Callable[[Screen], None]:
    """The step that knocks at ``door``, expects its question, and takes it back with Cancel, which keeps
    everything as it stood.
    """

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
    """Exits and answers Exit to the question about the reconstruction."""
    prompt = screen.reconstructions.unsaved_prompt
    screen.press_shortcut(ShortcutId.EXIT)
    screen.expect(prompt.is_shown, bool, description="the question about the reconstruction")

    prompt.confirm()

    assert screen.wait_for_exit()


class TestAnEditedReconstructionAtEveryDoor:
    """Every door asks about an edited reconstruction in its own words, and Cancel keeps everything as it
    stood.

    The reconstruction is open beside a project and its first level is raised. Each door is knocked at in
    turn; its question is compared with the expected title, words and answers, and Cancel leaves the title,
    file line, volume and windows as before. The scenario ends by exiting.
    """

    @pytest.fixture
    def startup(self) -> Startup:
        """Opens a reconstruction beside a project."""
        return Startup(reconstruction=OPEN_RECONSTRUCTION, project=SONG)

    def test_each_door_asks_its_question(self, screen: Screen) -> None:
        """Each door asks its own question and Cancel keeps the screen as it was."""

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
    """Every door asks about a reconstruction whose file was removed, as it asks about an edited one.

    The open reconstruction loses its file in the browser and shows as unsaved. Each door is knocked at in
    turn, asks its question, and Cancel keeps everything as it stood. The scenario ends by exiting.
    """

    @pytest.fixture
    def startup(self) -> Startup:
        """Opens a reconstruction beside a project."""
        return Startup(reconstruction=OPEN_RECONSTRUCTION, project=SONG)

    def test_each_door_asks_its_question(self, screen: Screen) -> None:
        """Each door asks its own question and Cancel keeps the screen as it was."""

        def remove_its_file(screen: Screen) -> None:
            expect_open(screen, OPEN_RECONSTRUCTION)

            remove_from_the_browser(screen, OPEN_RECONSTRUCTION)

            expect_title(screen, titled(screen, SONG.stem, marked(OPEN_RECONSTRUCTION.name, unsaved=True)))

        screen.scenario(
            remove_its_file,
            *(asks_and_cancel_keeps_it(door, voice=SONG_SAMPLE) for door in ASKING_DOORS),
            leave_letting_it_go,
        ).run()
