from functools import partial
from typing import Final, List

from automation.dearpygui.items.types import Item
from automation.screen import Screen
from sampletones_application.categories.elements.global_ import MenuElements
from sampletones_application.categories.hierarchy import Tab
from sampletones_application.utils.gui.shortcuts.ids import ShortcutId
from sampletones_core.constants.enums import ChannelName

EDIT_VOICE: Final[str] = "sequencer.voices.label.context_edit"


def voice_row(screen: Screen, name: str) -> Item:
    """The Voices card's row of the voice ``name``, on the Sequencer tab brought to the front."""
    screen.tabs.bring_to_front(Tab.SEQUENCER)
    voices = screen.sequencer.voices
    return screen.expect_item(partial(voices.row, name), description=f"the row of {name}")


def double_click_voice(screen: Screen, name: str) -> None:
    """Double-clicks the voice ``name``, which opens it on the Reconstructions tab."""
    screen.sequencer.voices.edit(voice_row(screen, name))


def open_voice_menu(screen: Screen, name: str) -> None:
    """Right-clicks the row of the voice ``name``, which opens its menu."""
    screen.sequencer.voices.right_click(voice_row(screen, name))
    screen.expect(screen.context_menu.is_shown, bool, description=f"the menu of {name}")


def open_voice(screen: Screen, name: str) -> None:
    """Opens the voice ``name`` on the Reconstructions tab through Edit on its row's menu."""
    open_voice_menu(screen, name)
    screen.context_menu.choose(screen.words(EDIT_VOICE))


def leave_letting_the_project_go(screen: Screen) -> None:
    """Exits, letting the changed project go at the question about it."""
    prompt = screen.project.unsaved_prompt
    screen.press_shortcut(ShortcutId.EXIT)
    screen.expect(prompt.is_shown, bool, description="the question about the project")

    prompt.confirm()

    assert screen.wait_for_exit()


def on_the_sequencer(screen: Screen) -> None:
    """Brings the Sequencer tab to the front and waits until the project's voices are listed."""
    screen.tabs.bring_to_front(Tab.SEQUENCER)
    screen.expect(screen.sequencer.voices.names, bool, description="the project's voices")


def checked(screen: Screen, group: MenuElements, label: str) -> bool:
    """Whether the entry labeled ``label`` in the menu ``group`` carries its check mark."""
    return next(entry.checked for entry in screen.menu.entries(group) if entry.label == label)


def sounding_but(*muted: ChannelName) -> List[bool]:
    """What Playback ▸ Channels marks while exactly ``muted`` are silenced, in channel order."""
    return [channel not in muted for channel in ChannelName.items()]


def channels_sounding(screen: Screen) -> List[bool]:
    """Which channels Playback ▸ Channels marks as sounding, in channel order."""
    return [
        checked(
            screen,
            MenuElements.GROUP_PLAYBACK_CHANNELS,
            screen.channel_words(channel),
        )
        for channel in ChannelName.items()
    ]
