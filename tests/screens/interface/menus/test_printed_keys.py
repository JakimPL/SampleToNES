from typing import Final, Tuple

from automation.screen import Screen
from sampletones_application.categories.elements.global_ import MenuElements
from sampletones_application.utils.gui.shortcuts.ids import ShortcutId

PRINTED: Final[Tuple[Tuple[MenuElements, MenuElements, ShortcutId], ...]] = (
    (MenuElements.GROUP_FILE, MenuElements.ITEM_FILE_NEW_PROJECT, ShortcutId.NEW_PROJECT),
    (MenuElements.GROUP_FILE, MenuElements.ITEM_FILE_OPEN_PROJECT, ShortcutId.OPEN_PROJECT),
    (MenuElements.GROUP_FILE, MenuElements.ITEM_FILE_SAVE_PROJECT, ShortcutId.SAVE_PROJECT),
    (MenuElements.GROUP_FILE, MenuElements.ITEM_FILE_SAVE_PROJECT_AS, ShortcutId.SAVE_PROJECT_AS),
    (MenuElements.GROUP_FILE, MenuElements.ITEM_FILE_PROJECT_PROPERTIES, ShortcutId.PROJECT_PROPERTIES),
    (MenuElements.GROUP_FILE, MenuElements.ITEM_FILE_RENDER_SONG, ShortcutId.RENDER_SONG),
    (MenuElements.GROUP_FILE, MenuElements.ITEM_FILE_CLOSE_PROJECT, ShortcutId.CLOSE_PROJECT),
    (MenuElements.GROUP_FILE, MenuElements.ITEM_FILE_EXIT, ShortcutId.EXIT),
    (MenuElements.GROUP_EDIT, MenuElements.ITEM_EDIT_UNDO, ShortcutId.UNDO),
    (MenuElements.GROUP_EDIT, MenuElements.ITEM_EDIT_REDO, ShortcutId.REDO),
    (
        MenuElements.GROUP_RECONSTRUCTION,
        MenuElements.ITEM_RECONSTRUCTION_RECONSTRUCT_FILE,
        ShortcutId.RECONSTRUCT_FILE,
    ),
    (
        MenuElements.GROUP_RECONSTRUCTION,
        MenuElements.ITEM_RECONSTRUCTION_RECONSTRUCT_DIRECTORY,
        ShortcutId.RECONSTRUCT_DIRECTORY,
    ),
    (MenuElements.GROUP_RECONSTRUCTION, MenuElements.ITEM_RECONSTRUCTION_OPEN, ShortcutId.OPEN_RECONSTRUCTION),
    (MenuElements.GROUP_RECONSTRUCTION, MenuElements.ITEM_RECONSTRUCTION_SAVE, ShortcutId.SAVE_RECONSTRUCTION),
    (
        MenuElements.GROUP_RECONSTRUCTION,
        MenuElements.ITEM_RECONSTRUCTION_SAVE_AS,
        ShortcutId.SAVE_RECONSTRUCTION_AS,
    ),
    (MenuElements.GROUP_RECONSTRUCTION, MenuElements.ITEM_RECONSTRUCTION_CLOSE, ShortcutId.CLOSE_RECONSTRUCTION),
    (
        MenuElements.GROUP_RECONSTRUCTION,
        MenuElements.ITEM_RECONSTRUCTION_EXPORT_WAV,
        ShortcutId.EXPORT_RECONSTRUCTION_WAV,
    ),
    (MenuElements.GROUP_PLAYBACK, MenuElements.ITEM_PLAYBACK_PLAY_FROM_START, ShortcutId.PLAY_FROM_START),
    (MenuElements.GROUP_PLAYBACK, MenuElements.ITEM_PLAYBACK_PLAY_FROM_FRAME, ShortcutId.PLAY_FROM_FRAME),
    (MenuElements.GROUP_PLAYBACK, MenuElements.ITEM_PLAYBACK_STOP, ShortcutId.STOP),
    (MenuElements.GROUP_PLAYBACK, MenuElements.ITEM_PLAYBACK_AUTOPLAY, ShortcutId.TOGGLE_AUTOPLAY),
    (MenuElements.GROUP_PLAYBACK, MenuElements.ITEM_PLAYBACK_LOOP_SONG, ShortcutId.TOGGLE_LOOP_SONG),
    (MenuElements.GROUP_PLAYBACK, MenuElements.ITEM_PLAYBACK_AUDIO_SETTINGS, ShortcutId.AUDIO_SETTINGS),
    (
        MenuElements.GROUP_PLAYBACK_CHANNELS,
        MenuElements.ITEM_PLAYBACK_UNMUTE_ALL_CHANNELS,
        ShortcutId.UNMUTE_ALL_CHANNELS,
    ),
    (MenuElements.GROUP_VIEW, MenuElements.ITEM_VIEW_SHOW_ADVANCED_SETTINGS, ShortcutId.TOGGLE_ADVANCED_SETTINGS),
    (MenuElements.GROUP_VIEW, MenuElements.ITEM_VIEW_FULLSCREEN, ShortcutId.TOGGLE_FULLSCREEN),
    (MenuElements.GROUP_VIEW, MenuElements.ITEM_VIEW_DISPLAY_SETTINGS, ShortcutId.DISPLAY_SETTINGS),
    (MenuElements.GROUP_VIEW, MenuElements.ITEM_VIEW_KEYBOARD_SETTINGS, ShortcutId.KEYBOARD_SETTINGS),
)


class TestPrintedKeysFollowTheScheme:
    """Each menu entry prints the keys the scheme in place gives the action it runs."""

    def test_each_entry_prints_its_keys(self, screen: Screen) -> None:
        for group, item, shortcut_id in PRINTED:
            entries = {entry.label: entry.keys for entry in screen.menu.entries(group)}
            assert screen.menu.label(item) in entries, f"{group} offers no {item}: {list(entries)}"
            assert entries[screen.menu.label(item)] == screen.shortcut_words(shortcut_id), f"{item}"
