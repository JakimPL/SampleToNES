from dataclasses import dataclass
from functools import partial
from typing import Final, List, Optional, Tuple

import pytest

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
from tests.suite.screens.application import Startup
from tests.suite.screens.dearpygui.geometry import Rect
from tests.suite.screens.dearpygui.items import is_tag_within, read_viewport, read_windows
from tests.suite.screens.dearpygui.keys import IMGUI_ESCAPE
from tests.suite.screens.screen import Screen
from tests.suite.screens.world import ARRANGED_PROJECT

STILL_FRAMES: Final[int] = 20
CENTER_TOLERANCE: Final[float] = 1.0
HALF: Final[float] = 2.0
SETTLING_DRAWN_FRAMES: Final[int] = 2


@dataclass(frozen=True)
class MenuDialog:
    """A dialog a menu entry opens, and the tag its window stands under."""

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


def dialog_box(window: str) -> Optional[Rect]:
    """The box of the shown window standing under ``window``, if one stands. Runs on the render thread."""
    return next(
        (reading.rect for reading in read_windows() if reading.shown and is_tag_within(reading.alias, window)),
        None,
    )


def is_centered(box: Rect, viewport: Rect) -> bool:
    return (
        abs(box.x + box.width / HALF - viewport.width / HALF) <= CENTER_TOLERANCE
        and abs(box.y + box.height / HALF - viewport.height / HALF) <= CENTER_TOLERANCE
    )


def is_inside(box: Rect, viewport: Rect) -> bool:
    return box.x >= 0 and box.y >= 0 and box.x + box.width <= viewport.width and box.y + box.height <= viewport.height


@pytest.fixture
def startup() -> Startup:
    return Startup(reconstruction=None, project=ARRANGED_PROJECT)


class TestEveryDialogOpensCentered:
    """On its first open of the session, every dialog a menu opens stands centered in the window and inside it, in
    one place on every frame from its third drawn frame on.

    A dialog whose content settles its height takes two frames to measure itself, as `dialogs.md` states, so the
    rule holds from the frame after those.
    """

    def test_each_dialog_on_its_first_open(self, screen: Screen) -> None:
        def opening(dialog: MenuDialog) -> None:
            with screen.record(partial(dialog_box, dialog.window)) as recording:
                screen.menu.choose(dialog.group, dialog.item)
                screen.expect(
                    lambda: screen.bridge.ask(partial(dialog_box, dialog.window)) is not None,
                    bool,
                    description=dialog.name,
                )
                screen.frames(STILL_FRAMES)

            boxes: List[Rect] = [box for box in recording.values() if box is not None][SETTLING_DRAWN_FRAMES:]
            viewport = screen.bridge.ask(read_viewport)
            assert boxes, f"{dialog.name} was drawn for {SETTLING_DRAWN_FRAMES} frames or fewer"
            assert all(box == boxes[0] for box in boxes), f"{dialog.name} moved: {boxes}"
            assert is_inside(boxes[0], viewport), f"{dialog.name} at {boxes[0]} in {viewport}"
            assert is_centered(boxes[0], viewport), f"{dialog.name} at {boxes[0]} in {viewport}"

            screen.hand.press_key(IMGUI_ESCAPE, modifiers=[])

            screen.expect(
                lambda: screen.bridge.ask(partial(dialog_box, dialog.window)) is None,
                bool,
                description=f"{dialog.name} closed",
            )

        def open_each_dialog_once(screen: Screen) -> None:
            for dialog in DIALOGS:
                opening(dialog)

        screen.scenario(open_each_dialog_once).run()
