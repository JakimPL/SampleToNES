import operator

from automation.screen import Screen
from automation.steps.main import convert_alone, home_path
from automation.steps.reconstructions import load_from_the_browser
from automation.steps.sequencer import double_click_voice, open_voice
from sampletones_application.utils.gui.shortcuts.ids import ShortcutId
from sampletones_core.constants.enums import ChannelName
from tests.screens.prompts.every_door.cases import Door
from tests.screens.prompts.every_door.constants import SETTLING_FRAMES
from tests.suite.screens.worlds.recordings import BASS, LEAD, OTHER_RECONSTRUCTION


def knock(screen: Screen, door: Door, *, voice: str) -> None:
    """Makes the gesture ``door`` stands for.

    A door that loads opens Other.stn, the run's bass, or ``voice``.
    """
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


def nothing_asked(screen: Screen) -> None:
    """Waits a few frames and expects every window to stay closed."""
    screen.frames(SETTLING_FRAMES)
    assert screen.shown_windows() == ()


def expect_title(screen: Screen, title: str) -> None:
    """Waits until the window title reads ``title``."""
    screen.expect(screen.title, title.__eq__, description=f"the title reading '{title}'")
