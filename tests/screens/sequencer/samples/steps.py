import operator
from functools import partial
from pathlib import Path

from sampletones_application.categories.hierarchy import Tab
from sampletones_application.tags.general import (
    TAG_GLOBAL_MENU_ITEM_RECONSTRUCTION_ADD_TO_SEQUENCER,
    TAG_GLOBAL_MENU_ITEM_VOICE_ADD_TO_SEQUENCER,
)
from sampletones_application.utils.gui.shortcuts.ids import ShortcutId
from sampletones_shared.constants.symbols import TITLE_SEPARATOR
from tests.screens.sequencer.samples.constants import (
    ADD_SAMPLE_FROM_FILE,
    ADD_TO_SEQUENCER,
    PROJECT_TITLE_PART,
    REPLACE_SAMPLE,
    SAMPLE_KEY,
    UNSOUND_FAILURE,
)
from tests.suite.screens.boundaries.dialogs import DialogKind
from tests.suite.screens.dearpygui.items.types import Item
from tests.suite.screens.screen import Screen
from tests.suite.screens.steps.reconstructions import BY_CONFIGURATION, expect_open
from tests.suite.screens.steps.sequencer import voice_row
from tests.suite.screens.views.browsers import FileTree


def listed_row(screen: Screen, browser: FileTree, path: Path) -> Item:
    """The row of ``path`` under the heading listing reconstructions by configuration in ``browser``.

    Every row above it that stands closed is opened with a click, so the row is in reach.
    """
    heading = screen.expect_item(
        partial(browser.heading, screen.words(BY_CONFIGURATION)),
        description="the heading listing reconstructions by configuration",
    )
    if not browser.is_open(heading):
        browser.open_by_click(heading)
        screen.expect(partial(browser.is_open, heading), bool, description="the heading open")

    row = screen.expect_item(partial(browser.file_row, path), description=f"the row of {path.name}")
    for above in browser.rows_above(row):
        if not browser.is_open(above):
            browser.open_by_click(above)
            screen.expect(partial(browser.is_open, above), bool, description=f"the rows above {path.name} open")

    return row


def choose_on_the_row(screen: Screen, browser: FileTree, path: Path, label: str) -> None:
    """Right-clicks the row of ``path`` in ``browser`` and clicks the entry reading ``label`` on its menu."""
    browser.right_click(listed_row(screen, browser, path))
    screen.expect(screen.context_menu.is_shown, bool, description=f"the menu of {path.name}")
    screen.context_menu.choose(label)


def add_from_the_reconstructions_browser(screen: Screen, path: Path) -> None:
    """Adds ``path`` through Add to Sequencer on its row's menu on the Reconstructions tab."""
    screen.tabs.bring_to_front(Tab.RECONSTRUCTIONS)
    choose_on_the_row(screen, screen.reconstructions.browser, path, screen.words(ADD_TO_SEQUENCER))


def add_from_the_sequencer_browser(screen: Screen, path: Path) -> None:
    """Adds ``path`` through Add to Sequencer on its row's menu on the Sequencer tab."""
    screen.tabs.bring_to_front(Tab.SEQUENCER)
    choose_on_the_row(screen, screen.sequencer.browser, path, screen.words(ADD_TO_SEQUENCER))


def add_by_double_click(screen: Screen, path: Path) -> None:
    """Adds ``path`` by double-clicking its row on the Sequencer tab."""
    screen.tabs.bring_to_front(Tab.SEQUENCER)
    browser = screen.sequencer.browser
    browser.double_click(listed_row(screen, browser, path))


def add_from_the_voices_list(screen: Screen, path: Path) -> None:
    """Adds ``path`` through Add sample from file... on the voices list's own menu, answering the file
    dialog with it.
    """
    screen.tabs.bring_to_front(Tab.SEQUENCER)
    screen.answer_next_dialog(DialogKind.OPEN, path)
    screen.sequencer.voices.right_click_below_the_rows()
    screen.expect(screen.context_menu.is_shown, bool, description="the menu of the voices list")
    screen.context_menu.choose(screen.words(ADD_SAMPLE_FROM_FILE))


def add_from_the_reconstruction_menu(screen: Screen, path: Path) -> None:
    """Opens ``path`` on the Reconstructions tab and adds it through Reconstruction ▸ Add to Sequencer."""
    add_the_open_document(screen, path, TAG_GLOBAL_MENU_ITEM_RECONSTRUCTION_ADD_TO_SEQUENCER)


def add_from_the_voice_menu(screen: Screen, path: Path) -> None:
    """Opens ``path`` on the Reconstructions tab and adds it through Voice ▸ Add to Sequencer."""
    add_the_open_document(screen, path, TAG_GLOBAL_MENU_ITEM_VOICE_ADD_TO_SEQUENCER)


def add_the_open_document(screen: Screen, path: Path, entry: str) -> None:
    """Opens ``path`` with a double click on the Reconstructions tab, and chooses the menu bar's ``entry``
    once it answers.
    """
    screen.tabs.bring_to_front(Tab.RECONSTRUCTIONS)
    browser = screen.reconstructions.browser
    browser.double_click(listed_row(screen, browser, path))
    expect_open(screen, path)
    screen.expect(
        partial(screen.menu.is_tagged_enabled, entry), bool, description=f"Add to Sequencer answering for {path.name}"
    )

    screen.menu.choose_tagged(entry)


def replace_entry(screen: Screen, label: str) -> str:
    """The words of the entry replacing the sample listed as ``label``, as the language file has them."""
    return screen.words(REPLACE_SAMPLE).format(**{SAMPLE_KEY: label})


def replace_from_the_sequencer_browser(
    screen: Screen,
    path: Path,
    *,
    voice: str,
    label: str,
) -> None:
    """Picks ``voice``, and replaces it with ``path`` through the Replace entry naming ``label`` on the row's
    menu on the Sequencer tab.
    """
    voices = screen.sequencer.voices
    voices.pick(voice_row(screen, voice))
    choose_on_the_row(screen, screen.sequencer.browser, path, replace_entry(screen, label))


def expect_refused(screen: Screen) -> str:
    """Waits for the error notice, reads it, takes the failure behind it as provoked and dismisses it.

    Returns:
        str: Everything the notice said.
    """
    notice = screen.error_notice
    screen.expect(notice.is_shown, bool, description="the error notice")
    words = notice.words()
    screen.claim_error(UNSOUND_FAILURE)

    notice.dismiss()

    screen.expect(notice.is_shown, operator.not_, description="the error notice dismissed")
    return words


def project_part(screen: Screen) -> str:
    """The piece of the window title naming the project, marked while it holds unsaved changes."""
    return screen.title().split(TITLE_SEPARATOR)[PROJECT_TITLE_PART]


def add_anyway(screen: Screen, path: Path) -> str:
    """Double-clicks ``path`` on the Sequencer tab and answers Add anyway to the question about its rate.

    Returns:
        str: Everything the question said.
    """
    prompt = screen.sequencer.frequency_prompt
    add_by_double_click(screen, path)
    screen.expect(prompt.is_shown, bool, description="the question about the rate")
    words = prompt.words()

    prompt.confirm()

    screen.expect(prompt.is_shown, operator.not_, description="the question answered")
    return words


def leave_unchanged(screen: Screen, project: str) -> None:
    """Exits while the project ``project`` holds nothing unsaved; the window closes at once."""
    assert project_part(screen) == project

    screen.press_shortcut(ShortcutId.EXIT)

    assert screen.wait_for_exit()
