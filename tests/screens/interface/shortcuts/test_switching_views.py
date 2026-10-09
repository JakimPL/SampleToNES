from functools import partial
from typing import Final, List, Tuple

from automation.screen import Screen
from automation.steps.reconstructions import expect_open
from automation.steps.sequencer import channels_sounding, checked
from automation.vocabulary.playback import PAUSE, PLAY
from sampletones_application.categories.elements.global_ import MenuElements
from sampletones_application.categories.hierarchy import Tab
from sampletones_application.utils.gui.shortcuts.ids import ShortcutId
from sampletones_core.constants.enums import ChannelName
from tests.screens.interface.shortcuts.steps import on_a_tab
from tests.suite.screens.worlds.recordings import PLAYABLE_RECONSTRUCTION

TAB_SHORTCUTS: Final[Tuple[Tuple[ShortcutId, Tab], ...]] = (
    (ShortcutId.SELECT_TAB_RECONSTRUCTIONS, Tab.RECONSTRUCTIONS),
    (ShortcutId.SELECT_TAB_SEQUENCER, Tab.SEQUENCER),
    (ShortcutId.SELECT_TAB_INSTRUCTIONS, Tab.INSTRUCTIONS),
    (ShortcutId.SELECT_TAB_MAIN, Tab.MAIN),
)

CHANNEL_SHORTCUTS: Final[Tuple[Tuple[ShortcutId, ChannelName], ...]] = (
    (ShortcutId.TOGGLE_CHANNEL_PULSE_1, ChannelName.PULSE1),
    (ShortcutId.TOGGLE_CHANNEL_PULSE_2, ChannelName.PULSE2),
    (ShortcutId.TOGGLE_CHANNEL_TRIANGLE, ChannelName.TRIANGLE),
    (ShortcutId.TOGGLE_CHANNEL_NOISE, ChannelName.NOISE),
)

CHECKED_SHORTCUTS: Final[Tuple[Tuple[ShortcutId, MenuElements, MenuElements], ...]] = (
    (ShortcutId.TOGGLE_AUTOPLAY, MenuElements.GROUP_PLAYBACK, MenuElements.ITEM_PLAYBACK_AUTOPLAY),
    (ShortcutId.TOGGLE_LOOP_SONG, MenuElements.GROUP_PLAYBACK, MenuElements.ITEM_PLAYBACK_LOOP_SONG),
    (ShortcutId.TOGGLE_ADVANCED_SETTINGS, MenuElements.GROUP_VIEW, MenuElements.ITEM_VIEW_SHOW_ADVANCED_SETTINGS),
)

FOLLOW_SHORTCUTS: Final[Tuple[Tuple[ShortcutId, MenuElements], ...]] = (
    (ShortcutId.FOLLOW_PATTERNS, MenuElements.ITEM_PLAYBACK_FOLLOW_PATTERNS),
    (ShortcutId.FOLLOW_OFF, MenuElements.ITEM_PLAYBACK_FOLLOW_OFF),
    (ShortcutId.FOLLOW_ROWS, MenuElements.ITEM_PLAYBACK_FOLLOW_ROWS),
)

FOLLOW_ITEMS: Final[Tuple[MenuElements, ...]] = tuple(item for _, item in FOLLOW_SHORTCUTS)


def followed(screen: Screen) -> List[bool]:
    """Which follow modes Playback ▸ Follow marks as checked, in menu order."""
    return [checked(screen, MenuElements.GROUP_PLAYBACK_FOLLOW, screen.menu.label(item)) for item in FOLLOW_ITEMS]


class TestShortcutsSwitchingWhatIsShown:
    """Each tab, channel, mode and playback shortcut changes what its menu entry or the screen says it
    changes.

    The scenario goes through the tab shortcuts, mutes and restores each channel, flips each checked
    entry twice, selects each follow mode, and starts and stops playback.
    """

    def test_each_switches_its_state(self, screen: Screen) -> None:
        playback = screen.sequencer.playback

        def tabs(screen: Screen) -> None:
            expect_open(screen, PLAYABLE_RECONSTRUCTION)
            for shortcut_id, tab in TAB_SHORTCUTS:
                screen.press_shortcut(shortcut_id)

                screen.expect(screen.tabs.front, tab.__eq__, description=f"{tab} in front")

            screen.press_shortcut(ShortcutId.NEXT_TAB)
            screen.expect(screen.tabs.front, Tab.RECONSTRUCTIONS.__eq__, description="the next tab in front")
            screen.press_shortcut(ShortcutId.PREVIOUS_TAB)
            screen.expect(screen.tabs.front, Tab.MAIN.__eq__, description="the previous tab in front")

        def channels(screen: Screen) -> None:
            on_a_tab(screen, Tab.SEQUENCER)
            for index, (shortcut_id, channel) in enumerate(CHANNEL_SHORTCUTS):
                screen.press_shortcut(shortcut_id)

                expected = [position > index for position in range(len(CHANNEL_SHORTCUTS))]
                screen.expect(partial(channels_sounding, screen), expected.__eq__, description=f"{channel} muted")

            for shortcut_id, channel in CHANNEL_SHORTCUTS:
                screen.press_shortcut(shortcut_id)

            screen.expect(partial(channels_sounding, screen), all, description="every channel sounding again")

        def switches(screen: Screen) -> None:
            for shortcut_id, group, item in CHECKED_SHORTCUTS:
                on_a_tab(screen, Tab.SEQUENCER)
                before = screen.menu.is_checked(group, item)

                screen.press_shortcut(shortcut_id)

                screen.expect(
                    lambda: screen.menu.is_checked(group, item),
                    (not before).__eq__,
                    description=f"{item} switched",
                )
                screen.press_shortcut(shortcut_id)
                screen.expect(lambda: screen.menu.is_checked(group, item), before.__eq__, description=f"{item} back")

        def follow_modes(screen: Screen) -> None:
            for index, (shortcut_id, item) in enumerate(FOLLOW_SHORTCUTS):
                screen.press_shortcut(shortcut_id)

                expected = [position == index for position in range(len(FOLLOW_ITEMS))]
                screen.expect(partial(followed, screen), expected.__eq__, description=f"{item} alone checked")

        def play_and_stop(screen: Screen) -> None:
            for start in (ShortcutId.PLAY, ShortcutId.PLAY_FROM_START):
                screen.press_shortcut(start)
                screen.expect(playback.play_entry, screen.words(PAUSE).__eq__, description=f"playing after {start}")

                screen.press_shortcut(ShortcutId.STOP)

                screen.expect(playback.play_entry, screen.words(PLAY).__eq__, description="stopped")

        screen.scenario(tabs, channels, switches, follow_modes, play_and_stop).run()
