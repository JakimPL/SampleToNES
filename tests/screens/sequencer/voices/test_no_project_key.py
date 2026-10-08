import operator
from typing import Final

import pytest

from automation.application.startup import Startup
from automation.screen import Screen
from automation.steps.sequencer import leave_letting_the_project_go
from automation.worlds.home import World
from sampletones_application.categories.hierarchy import Tab
from sampletones_application.config.session.application.config import ApplicationConfig
from sampletones_application.config.session.application.shortcuts import ShortcutsConfig
from sampletones_application.utils.gui.keyboard.combination import KeyCombination
from sampletones_application.utils.gui.shortcuts.ids import ShortcutId
from tests.suite.screens.worlds.songs import sequencer_world

NEW_INSTRUMENT_KEYS: Final[KeyCombination] = KeyCombination.parse("F12")
NO_PROJECT_TITLE: Final[str] = "global.dialog.title.no_project_open"
NO_PROJECT_MESSAGE: Final[str] = "global.dialog.message.no_project_open"
SETTLING_FRAMES: Final[int] = 20


@pytest.fixture
def world() -> World:
    """The Sequencer's home, its settings giving New instrument a key of its own."""
    sequencer = sequencer_world()
    return World(
        state=sequencer.state,
        application_config=ApplicationConfig(
            shortcuts=ShortcutsConfig(
                overrides={ShortcutId.NEW_INSTRUMENT.value: NEW_INSTRUMENT_KEYS.display()},
            ),
        ),
        config=None,
        files=sequencer.files,
    )


@pytest.fixture
def startup() -> Startup:
    """The application opens with no project and no reconstruction."""
    return Startup(reconstruction=None, project=None)


class TestTheNewInstrumentKeyWithNoProjectOpen:
    """With no project open, the key given to New instrument tells the reader to open a project and adds no voice.

    The key brings up the notice in the words the language file gives it, OK dismisses it, and the voice list
    stays empty. A new project then takes the same key, which adds one voice.
    """

    def test_the_key_tells_the_reader_and_adds_nothing(self, screen: Screen) -> None:
        voices = screen.sequencer.voices
        notice = screen.no_project_notice

        def the_key_tells_the_reader(screen: Screen) -> None:
            screen.tabs.bring_to_front(Tab.SEQUENCER)
            screen.frames(SETTLING_FRAMES)
            assert voices.names() == []

            screen.press_shortcut(ShortcutId.NEW_INSTRUMENT)

            screen.expect(notice.is_shown, bool, description="the notice that no project is open")
            assert notice.prompt.title() == screen.words(NO_PROJECT_TITLE)
            assert notice.words() == screen.words(NO_PROJECT_MESSAGE)
            notice.dismiss()
            screen.expect(notice.is_shown, operator.not_, description="the notice dismissed")
            assert voices.names() == []

        def a_new_project_takes_the_key(screen: Screen) -> None:
            screen.project.create()
            screen.expect(voices.new_instrument_answers, bool, description="New instrument answering")

            screen.press_shortcut(ShortcutId.NEW_INSTRUMENT)

            screen.expect(lambda: len(voices.names()), (1).__eq__, description="one voice")
            assert not notice.is_shown()

        screen.scenario(
            the_key_tells_the_reader,
            a_new_project_takes_the_key,
            leave_letting_the_project_go,
        ).run()
