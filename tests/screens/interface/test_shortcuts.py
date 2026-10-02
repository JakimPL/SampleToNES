import operator
from functools import partial
from typing import Final, List, Tuple

import pytest

from sampletones_application.categories.elements.global_ import MenuElements
from sampletones_application.categories.hierarchy import Tab
from sampletones_application.tags.settings import (
    TAG_SETTINGS_AUDIO_WINDOW,
    TAG_SETTINGS_DISPLAY_WINDOW,
    TAG_SETTINGS_KEYBINDINGS_WINDOW,
    TAG_SETTINGS_PROPERTIES_WINDOW,
    TAG_SETTINGS_RENDER_WINDOW,
)
from sampletones_application.utils.gui.shortcuts.ids import ShortcutId
from sampletones_core.constants.enums import ChannelName
from tests.suite.screens.application import Startup
from tests.suite.screens.boundaries.dialogs import DialogKind
from tests.suite.screens.dearpygui.items import is_tag_within, read_windows
from tests.suite.screens.dearpygui.keys import IMGUI_ESCAPE
from tests.suite.screens.screen import Screen
from tests.suite.screens.steps.reconstructions import UNTITLED, expect_open, titled
from tests.suite.screens.world import ARRANGED_PROJECT, PLAYABLE_RECONSTRUCTION

PAUSE: Final[str] = "global.menu.label.item_playback_pause"
PLAY: Final[str] = "global.menu.label.item_playback_play"
SETTLING_FRAMES: Final[int] = 10
DIALOG_SHORTCUTS: Final[Tuple[Tuple[ShortcutId, str], ...]] = (
    (ShortcutId.DISPLAY_SETTINGS, TAG_SETTINGS_DISPLAY_WINDOW),
    (ShortcutId.KEYBOARD_SETTINGS, TAG_SETTINGS_KEYBINDINGS_WINDOW),
    (ShortcutId.AUDIO_SETTINGS, TAG_SETTINGS_AUDIO_WINDOW),
    (ShortcutId.PROJECT_PROPERTIES, TAG_SETTINGS_PROPERTIES_WINDOW),
    (ShortcutId.RENDER_SONG, TAG_SETTINGS_RENDER_WINDOW),
)
FILE_SHORTCUTS: Final[Tuple[Tuple[ShortcutId, DialogKind], ...]] = (
    (ShortcutId.SAVE_PROJECT_AS, DialogKind.SAVE),
    (ShortcutId.EXPORT_PROJECT_FAMITRACKER, DialogKind.SAVE),
    (ShortcutId.EXPORT_PROJECT_BITPHASE, DialogKind.SAVE),
    (ShortcutId.RECONSTRUCT_FILE, DialogKind.OPEN),
    (ShortcutId.RECONSTRUCT_DIRECTORY, DialogKind.DIRECTORY),
    (ShortcutId.OPEN_RECONSTRUCTION, DialogKind.OPEN),
    (ShortcutId.SAVE_RECONSTRUCTION_AS, DialogKind.SAVE),
    (ShortcutId.EXPORT_RECONSTRUCTION_WAV, DialogKind.SAVE),
    (ShortcutId.EXPORT_INSTRUMENTS_FAMITRACKER, DialogKind.SAVE),
)
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


def window_standing(window: str) -> bool:
    """Whether a window standing under ``window`` is shown. Runs on the render thread."""
    return any(reading.shown and is_tag_within(reading.alias, window) for reading in read_windows())


def checked(screen: Screen, group: MenuElements, label: str) -> bool:
    return next(entry.checked for entry in screen.menu.entries(group) if entry.label == label)


def sounding(screen: Screen) -> List[bool]:
    """Which channels Playback ▸ Channels marks as sounding, in channel order."""
    return [
        checked(screen, MenuElements.GROUP_PLAYBACK_CHANNELS, screen.channel_words(channel))
        for channel in ChannelName.items()
    ]


def followed(screen: Screen) -> List[bool]:
    return [checked(screen, MenuElements.GROUP_PLAYBACK_FOLLOW, screen.menu.label(item)) for item in FOLLOW_ITEMS]


def on_a_tab(screen: Screen, tab: Tab) -> None:
    """Brings ``tab`` forward with a click, which leaves no field holding the keyboard."""
    screen.tabs.bring_to_front(tab)
    screen.frames(SETTLING_FRAMES)


@pytest.fixture
def startup() -> Startup:
    return Startup(reconstruction=PLAYABLE_RECONSTRUCTION, project=ARRANGED_PROJECT)


class TestShortcutsOpeningDialogs:
    """Each shortcut printed for a dialog opens that dialog, and each one printed for a file asks for that file."""

    def test_each_opens_what_it_names(self, screen: Screen) -> None:
        def each_dialog_shortcut(screen: Screen) -> None:
            expect_open(screen, PLAYABLE_RECONSTRUCTION)
            for shortcut_id, window in DIALOG_SHORTCUTS:
                on_a_tab(screen, Tab.RECONSTRUCTIONS)

                screen.press_shortcut(shortcut_id)

                screen.expect(lambda: screen.bridge.ask(partial(window_standing, window)), bool, description=window)
                screen.hand.press_key(IMGUI_ESCAPE, modifiers=[])
                screen.expect(
                    lambda: screen.bridge.ask(partial(window_standing, window)),
                    operator.not_,
                    description=f"{window} closed",
                )

        def each_file_shortcut(screen: Screen) -> None:
            for shortcut_id, kind in FILE_SHORTCUTS:
                on_a_tab(screen, Tab.RECONSTRUCTIONS)
                asked = len(screen.dialog_requests())
                screen.answer_next_dialog(kind, None)

                screen.press_shortcut(shortcut_id)

                screen.expect(
                    lambda: len(screen.dialog_requests()),
                    (asked + 1).__eq__,
                    description=f"the file {shortcut_id} asks for",
                )
                assert screen.dialog_requests()[-1].kind == kind

        def open_project_asks_about_the_open_one_first(screen: Screen) -> None:
            prompt = screen.project.replace_prompt
            on_a_tab(screen, Tab.SEQUENCER)
            asked = len(screen.dialog_requests())
            screen.press_shortcut(ShortcutId.OPEN_PROJECT)
            screen.expect(prompt.is_shown, bool, description="the question about the open project")

            prompt.cancel()

            screen.expect(prompt.is_shown, operator.not_, description="the question taken back")
            screen.frames(SETTLING_FRAMES)
            assert len(screen.dialog_requests()) == asked
            screen.answer_next_dialog(DialogKind.OPEN, None)
            screen.press_shortcut(ShortcutId.OPEN_PROJECT)
            screen.expect(prompt.is_shown, bool, description="the question again")
            prompt.confirm()
            screen.expect(
                lambda: len(screen.dialog_requests()), (asked + 1).__eq__, description="the project asked for"
            )
            assert screen.dialog_requests()[-1].kind == DialogKind.OPEN

        screen.scenario(each_dialog_shortcut, each_file_shortcut, open_project_asks_about_the_open_one_first).run()


class TestShortcutsSwitchingWhatIsShown:
    """Each tab, channel, mode and playback shortcut changes what its menu entry or the screen says it changes."""

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
                screen.expect(partial(sounding, screen), expected.__eq__, description=f"{channel} muted")

            for shortcut_id, channel in CHANNEL_SHORTCUTS:
                screen.press_shortcut(shortcut_id)

            screen.expect(partial(sounding, screen), all, description="every channel sounding again")

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


class TestShortcutsActingOnDocuments:
    """Each shortcut closing or starting a document does what its entry says."""

    def test_each_acts_as_named(self, screen: Screen) -> None:
        voices = screen.sequencer.voices
        reconstructions = screen.reconstructions

        def documents_close_and_a_new_project_opens(screen: Screen) -> None:
            expect_open(screen, PLAYABLE_RECONSTRUCTION)
            on_a_tab(screen, Tab.SEQUENCER)
            screen.press_shortcut(ShortcutId.CLOSE_RECONSTRUCTION)
            screen.expect(reconstructions.file_line, operator.not_, description="the reconstruction closed")

            screen.press_shortcut(ShortcutId.CLOSE_PROJECT)
            screen.expect(voices.names, operator.not_, description="the project closed")

            screen.press_shortcut(ShortcutId.NEW_PROJECT)

            screen.expect(screen.title, titled(screen, screen.words(UNTITLED)).__eq__, description="a new project")

        def exit_leaves(screen: Screen) -> None:
            screen.press_shortcut(ShortcutId.EXIT)

            assert screen.wait_for_exit()

        screen.scenario(documents_close_and_a_new_project_opens, exit_leaves).run()
