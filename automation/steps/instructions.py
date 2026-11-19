from functools import partial
from pathlib import Path

from automation.dearpygui.items.types import Item
from automation.screen import Screen
from automation.steps.trees import set_open
from sampletones_application.categories.hierarchy import Tab
from sampletones_core.configs import Config
from sampletones_core.fft import Window
from sampletones_core.library.key import InstructionLibraryKey
from sampletones_core.library.settings import LibrarySettings
from sampletones_shared.paths.user import LIBRARY_DIRECTORY


def library_path(config: Config) -> Path:
    """Where the library built for ``config`` is stored, under the name its settings give it."""
    key = InstructionLibraryKey.create(LibrarySettings.of(config), Window.from_config(config))
    return LIBRARY_DIRECTORY / key.filename


def library_row(screen: Screen, path: Path) -> Item:
    """The library card's row of the library stored at ``path``, once it is drawn."""
    library = screen.instructions.library
    return screen.expect_item(partial(library.row, path.name), description=f"the row of {path.name}")


def open_library_row(screen: Screen, row: Item) -> None:
    """Opens a library's row, which is the click that loads it, closing it first where it stands open."""
    tree = screen.instructions.library.tree
    set_open(screen, tree, row, opened=False)
    tree.click(row)


def load_library(screen: Screen, config: Config) -> Item:
    """Brings the Instructions tab forward and opens the row of the library built for ``config``, which loads
    it.
    """
    screen.tabs.bring_to_front(Tab.INSTRUCTIONS)
    row = library_row(screen, library_path(config))
    open_library_row(screen, row)
    return row
