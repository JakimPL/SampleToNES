import operator
from functools import partial
from pathlib import Path
from typing import Dict, Final, Sequence

from sampletones_application.categories.hierarchy import Tab
from sampletones_core.constants.enums import ChannelName
from tests.suite.screens.dearpygui.items import Item
from tests.suite.screens.screen import Screen

RUN_TIMEOUT_SECONDS: Final[float] = 120.0


def home_path(name: str) -> Path:
    """A path in the home the application was started in, which the explorer stands open on."""
    return Path.cwd() / name


def explorer_row(screen: Screen, path: Path) -> Item:
    """The explorer's row of ``path``, once it is drawn."""
    return screen.expect_item(lambda: screen.explorer.file_row(path), description=f"the explorer's row of {path.name}")


def gather(screen: Screen, *paths: Path) -> None:
    """Ctrl-clicks each of ``paths`` in the explorer, waiting for the button to name the larger run.

    A long list draws only the rows in view, so the button counting the run is what shows a
    recording joined it.
    """
    converter = screen.main.converter
    for path in paths:
        before = converter.action()
        screen.explorer.ctrl_click(explorer_row(screen, path))
        screen.expect(converter.action, before.__ne__, description=f"{path.name} gathered")
        screen.expect(lambda: not converter.scan_shown(), bool, description="the folder read")


def choose_from_the_row_menu(screen: Screen, path: Path, entry: str) -> None:
    """Right-clicks the converter's row of ``path`` and chooses ``entry`` from its menu."""
    row = screen.main.converter.list.row(path)
    screen.hand.scroll_into_view(row)
    screen.hand.right_click(row)
    screen.expect(screen.context_menu.is_shown, bool, description=f"the menu of {path.name}")
    screen.context_menu.choose(entry)


def give_each_its_own_channel(screen: Screen, channels: Dict[Path, ChannelName]) -> None:
    """Leaves each gathered recording the one channel ``channels`` names for it."""
    listing = screen.main.converter.list
    for path, keep in channels.items():
        for channel in ChannelName:
            if listing.channel_ticked(path, channel) != (channel == keep):
                listing.tick(path, channel)
                screen.expect(
                    partial(listing.channel_ticked, path, channel),
                    (channel == keep).__eq__,
                    description=f"{path.name} {channel}",
                )


def convert_alone(
    screen: Screen,
    recording: Path,
    *,
    channel: ChannelName,
    replacing: Sequence[Path],
) -> None:
    """Converts ``recording`` alone on ``channel``, and waits for the question the run's end asks.

    The recordings of ``replacing`` the list holds leave it first, and ``channel`` is the one
    channel the run may sound.
    """
    converter = screen.main.converter
    screen.tabs.bring_to_front(Tab.MAIN)
    for gathered in replacing:
        if converter.list.has_row(gathered):
            converter.list.remove(gathered)
            screen.expect(partial(converter.list.has_row, gathered), operator.not_, description=f"{gathered.name} gone")

    gather(screen, recording)
    give_each_its_own_channel(screen, {recording: channel})
    converter.press_action()

    screen.bridge.expect(converter.end_prompt.is_shown, bool, description="the run's end", timeout=RUN_TIMEOUT_SECONDS)
