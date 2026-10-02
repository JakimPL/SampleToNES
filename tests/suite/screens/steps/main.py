from pathlib import Path

from tests.suite.screens.dearpygui.items import Item
from tests.suite.screens.screen import Screen


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
