import operator
from pathlib import Path
from typing import Final, List, Optional

from sampletones_application.categories.hierarchy import Tab
from sampletones_core.constants.enums import ChannelName, FeatureKey
from sampletones_core.instructions import PulseInstruction
from sampletones_core.reconstructions import Reconstruction
from sampletones_shared.constants.symbols import TITLE_SEPARATOR
from sampletones_shared.paths.user import RECONSTRUCTIONS_DIRECTORY
from tests.suite.screens.dearpygui.items import Item
from tests.suite.screens.holds import RegenerationHold
from tests.suite.screens.screen import Screen

APPLICATION_NAME: Final[str] = "global.dialog.title.main_window"
UNTITLED: Final[str] = "global.dialog.label.untitled"
BY_CONFIGURATION: Final[str] = "global.browser.label.by_configuration"
REMOVE_RECONSTRUCTION: Final[str] = "reconstructions.browser.label.context_remove_reconstruction"
UNSAVED_MARK: Final[str] = "*"
LOUDEST: Final[int] = 15
ITEM_SEPARATOR: Final[str] = " "
RECONSTRUCTION_SUFFIX: Final[str] = ".stn"


def marked(name: str, *, unsaved: bool) -> str:
    """A document's name as the title bar carries it, marked while it holds unsaved changes."""
    return f"{name}{UNSAVED_MARK}" if unsaved else name


def titled(screen: Screen, *documents: str) -> str:
    """The window title naming ``documents`` after the application, each as the title bar marks it."""
    return TITLE_SEPARATOR.join((screen.words(APPLICATION_NAME), *documents))


def reconstruction_row(screen: Screen, path: Path) -> Item:
    """The browser's row of the reconstruction at ``path``, under the heading listing reconstructions by configuration.

    The heading is opened where it stands closed, so the row is in reach.
    """
    browser = screen.reconstructions.browser
    heading = screen.expect_item(
        lambda: browser.heading(screen.words(BY_CONFIGURATION)),
        description="the heading listing reconstructions by configuration",
    )
    if not browser.is_open(heading):
        browser.open_by_click(heading)
        screen.expect(lambda: browser.is_open(heading), bool, description="the heading open")

    return screen.expect_item(lambda: browser.file_row(path), description=f"the row of {path.name}")


def load_from_the_browser(screen: Screen, path: Path) -> None:
    """Double-clicks the browser's row of ``path``, which loads it once nothing unsaved stands in the way."""
    screen.tabs.bring_to_front(Tab.RECONSTRUCTIONS)
    screen.reconstructions.browser.double_click(reconstruction_row(screen, path))


def expect_open(screen: Screen, path: Path) -> None:
    """Waits until the reconstruction stored at ``path`` is the one open."""
    screen.expect(
        lambda: screen.reconstructions.shows_open(path),
        bool,
        description=f"{path.name} open",
    )


def edit_envelope(
    screen: Screen,
    *,
    channel: ChannelName,
    feature: FeatureKey,
    sequence: str,
    title: str,
) -> None:
    """Types ``sequence`` over a channel's envelope and waits for the edit to land, which marks the title ``title``."""
    screen.tabs.bring_to_front(Tab.RECONSTRUCTIONS)
    screen.reconstructions.type_envelope(channel, feature, sequence)
    screen.expect(screen.title, title.__eq__, description=f"the title reading '{title}'")


def remove_from_the_browser(screen: Screen, path: Path) -> None:
    """Removes the reconstruction at ``path`` through its row's menu, answering Remove to the question."""
    reconstructions = screen.reconstructions
    screen.tabs.bring_to_front(Tab.RECONSTRUCTIONS)
    reconstructions.browser.right_click(reconstruction_row(screen, path))
    screen.expect(screen.context_menu.is_shown, bool, description=f"the menu of {path.name}")
    screen.context_menu.choose(screen.words(REMOVE_RECONSTRUCTION))
    screen.expect(reconstructions.remove_prompt.is_shown, bool, description="the question about removing")

    reconstructions.remove_prompt.confirm()

    screen.expect(reconstructions.remove_prompt.is_shown, operator.not_, description="the question gone")
    screen.expect(path.exists, operator.not_, description=f"{path.name} gone")


def voice_title(screen: Screen, project: Optional[str], ordinal: int, voice: str, *, unsaved: bool) -> str:
    """The window title while a project's sample stands open: the project, marked, and the sample in brackets.

    The sample is named by its place among the voices, counted from zero in hexadecimal, and its name.
    """
    name = marked(project or screen.words(UNTITLED), unsaved=unsaved)
    return titled(screen, f"{name} [{ordinal:02X}: {voice}]")


def raised(level: int) -> int:
    """``level`` one step louder, wrapping past the loudest to silence."""
    return (level + 1) % (LOUDEST + 1)


def first_raised(sequence: str) -> str:
    """A volume sequence as typed, its first level one step louder."""
    first, *rest = sequence.split(ITEM_SEPARATOR)
    return ITEM_SEPARATOR.join((str(raised(int(first))), *rest))


def first_level_raised(levels: List[int]) -> List[int]:
    """The volume of each frame, the first frame's one step louder."""
    first, *rest = levels
    return [raised(first), *rest]


def leading(levels: List[int], frames: List[int]) -> List[int]:
    """The first of ``levels``, as many as ``frames`` holds: the frames a document had before an edit."""
    return levels[: len(frames)]


def stored_levels(path: Path, channel: ChannelName) -> List[int]:
    """The volume each frame of a pulse ``channel`` plays at in the reconstruction stored at ``path``."""
    instructions = Reconstruction.load(path).instructions[channel]
    return [instruction.volume for instruction in instructions if isinstance(instruction, PulseInstruction)]


def raise_the_first_level(
    screen: Screen,
    channel: ChannelName,
    *,
    title: str,
) -> str:
    """Raises the first volume of ``channel`` one step and waits for the title to read ``title``.

    Returns:
        str: The sequence typed.
    """
    screen.tabs.bring_to_front(Tab.RECONSTRUCTIONS)
    sequence = first_raised(
        screen.expect(
            lambda: screen.reconstructions.envelope(channel, FeatureKey.VOLUME),
            bool,
            description=f"the volume of {channel} drawn",
        )
    )
    edit_envelope(
        screen,
        channel=channel,
        feature=FeatureKey.VOLUME,
        sequence=sequence,
        title=title,
    )
    return sequence


def converted(recording: Path) -> Path:
    """The one reconstruction a run wrote for ``recording``, wherever below the reconstructions folder it went."""
    found = list(RECONSTRUCTIONS_DIRECTORY.rglob(f"{recording.stem}{RECONSTRUCTION_SUFFIX}"))
    assert len(found) == 1, found
    return found[0]


def raise_the_first_level_while_held(screen: Screen, hold: RegenerationHold, channel: ChannelName) -> str:
    """Raises the first volume of ``channel`` one step and waits for its rebuild to stand held.

    Returns:
        str: The sequence typed.
    """
    reconstructions = screen.reconstructions
    sequence = first_raised(reconstructions.envelope(channel, FeatureKey.VOLUME))

    reconstructions.type_envelope(channel, FeatureKey.VOLUME, sequence)

    screen.expect(hold.waiting, bool, description="the rebuild held")
    return sequence
