from functools import partial
from pathlib import Path
from typing import Final

from automation.dearpygui.items.types import Item
from automation.screen import Screen
from automation.views.browsers import FileTree

BY_CONFIGURATION: Final[str] = "global.browser.label.by_configuration"


def set_open(screen: Screen, tree: FileTree, row: Item, *, opened: bool) -> None:
    """Clicks ``row`` where it stands other than ``opened`` asks, and waits for it to stand so."""
    if tree.is_open(row) == opened:
        return

    tree.click(row)
    screen.expect(
        partial(tree.is_open, row),
        opened.__eq__,
        description=f"{tree.label(row)} {'open' if opened else 'closed'}",
    )


def listed_row(screen: Screen, browser: FileTree, path: Path) -> Item:
    """The row of ``path`` under the heading listing reconstructions by configuration in ``browser``.

    The heading and every row above the reconstruction's are opened where they stand closed, so the
    row is in reach.
    """
    heading = screen.expect_item(
        partial(browser.heading, screen.words(BY_CONFIGURATION)),
        description="the heading listing reconstructions by configuration",
    )
    set_open(screen, browser, heading, opened=True)

    row = screen.expect_item(partial(browser.file_row, path), description=f"the row of {path.name}")
    for above in browser.rows_above(row):
        set_open(screen, browser, above, opened=True)

    return row
