from dataclasses import dataclass
from typing import Final, Tuple

from sampletones_application.categories.elements.global_ import MenuElements
from sampletones_application.tags.general import TAG_GLOBAL_DIALOG_ABOUT
from sampletones_application.tags.settings import (
    TAG_SETTINGS_AUDIO_WINDOW,
    TAG_SETTINGS_DISPLAY_WINDOW,
    TAG_SETTINGS_KEYBINDINGS_WINDOW,
    TAG_SETTINGS_NSF_WINDOW,
    TAG_SETTINGS_PROPERTIES_WINDOW,
    TAG_SETTINGS_RENDER_WINDOW,
)


@dataclass(frozen=True)
class MenuDialog:
    """A dialog a menu entry opens.

    Attributes:
        name: The dialog's name in messages.
        group: The menu that holds the entry.
        item: The entry that opens the dialog.
        window: The tag its window stands under.
    """

    name: str
    group: MenuElements
    item: MenuElements
    window: str


DIALOGS: Final[Tuple[MenuDialog, ...]] = (
    MenuDialog(
        "Display settings",
        MenuElements.GROUP_VIEW,
        MenuElements.ITEM_VIEW_DISPLAY_SETTINGS,
        TAG_SETTINGS_DISPLAY_WINDOW,
    ),
    MenuDialog(
        "Keyboard shortcuts",
        MenuElements.GROUP_VIEW,
        MenuElements.ITEM_VIEW_KEYBOARD_SETTINGS,
        TAG_SETTINGS_KEYBINDINGS_WINDOW,
    ),
    MenuDialog(
        "Audio settings",
        MenuElements.GROUP_PLAYBACK,
        MenuElements.ITEM_PLAYBACK_AUDIO_SETTINGS,
        TAG_SETTINGS_AUDIO_WINDOW,
    ),
    MenuDialog(
        "Project properties",
        MenuElements.GROUP_FILE,
        MenuElements.ITEM_FILE_PROJECT_PROPERTIES,
        TAG_SETTINGS_PROPERTIES_WINDOW,
    ),
    MenuDialog(
        "Render song",
        MenuElements.GROUP_FILE,
        MenuElements.ITEM_FILE_RENDER_SONG,
        TAG_SETTINGS_RENDER_WINDOW,
    ),
    MenuDialog(
        "NSF program",
        MenuElements.GROUP_FILE,
        MenuElements.ITEM_FILE_EXPORT_NSF,
        TAG_SETTINGS_NSF_WINDOW,
    ),
    MenuDialog(
        "About",
        MenuElements.GROUP_HELP,
        MenuElements.ITEM_HELP_ABOUT,
        TAG_GLOBAL_DIALOG_ABOUT,
    ),
)
