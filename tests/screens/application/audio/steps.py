from automation.screen import Screen
from automation.vocabulary.playback import PAUSE
from sampletones_application.categories.elements.global_ import MenuElements
from sampletones_application.categories.hierarchy import Tab
from sampletones_application.utils.gui.shortcuts.ids import ShortcutId


def song_loops(screen: Screen) -> bool:
    """Whether Playback ▸ Loop song carries its check mark."""
    return screen.menu.is_checked(MenuElements.GROUP_PLAYBACK, MenuElements.ITEM_PLAYBACK_LOOP_SONG)


def play_the_looping_song(screen: Screen) -> None:
    """Turns Loop song on and plays the song from the Sequencer tab, so the song plays until something ends it."""
    screen.tabs.bring_to_front(Tab.SEQUENCER)
    if not song_loops(screen):
        screen.press_shortcut(ShortcutId.TOGGLE_LOOP_SONG)
        screen.expect(lambda: song_loops(screen), bool, description="Loop song on")

    play_the_song(screen)


def play_the_song(screen: Screen) -> None:
    """Presses Play on the Sequencer tab and waits for the song to play."""
    screen.press_shortcut(ShortcutId.PLAY)
    screen.expect(screen.sequencer.playback.play_entry, screen.words(PAUSE).__eq__, description="playing")
