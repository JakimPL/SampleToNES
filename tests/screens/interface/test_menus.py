from typing import Final, List, Tuple

import numpy as np
import pytest

from sampletones_application.categories.elements.global_ import MenuElements
from sampletones_application.utils.gui.shortcuts.ids import ShortcutId
from sampletones_application.utils.palette.catalog import DEFAULT_PALETTE_NAME
from tests.suite.screens.application import Startup
from tests.suite.screens.dearpygui.geometry import Point
from tests.suite.screens.palettes import Color, shipped_palettes, token_color
from tests.suite.screens.screen import Screen
from tests.suite.screens.world import ARRANGED_PROJECT, PLAYABLE_RECONSTRUCTION

POPUP_TOKEN: Final[str] = "popup"
RGB: Final[int] = 3
COLOR_TOLERANCE: Final[float] = 1.5 / 255.0
LEFT_INSET: Final[int] = 4
OPENING_FRAMES: Final[int] = 5
READINGS: Final[int] = 8
FRAMES_BETWEEN_READINGS: Final[int] = 3
MENUS: Final[Tuple[MenuElements, ...]] = (
    MenuElements.GROUP_FILE,
    MenuElements.GROUP_EDIT,
    MenuElements.GROUP_RECONSTRUCTION,
    MenuElements.GROUP_VOICE,
    MenuElements.GROUP_PLAYBACK,
    MenuElements.GROUP_VIEW,
    MenuElements.GROUP_HELP,
)
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


def popup_right_edge(pixels: np.ndarray, header: Point, background: Color) -> int:
    """The last column the popup below ``header`` paints in its background, on the rows it spans.

    The popup's rows are those its background reaches just inside its left edge, under the header.
    """
    painted = np.all(np.abs(pixels[:, :, :RGB] - np.array(background[:RGB])) <= COLOR_TOLERANCE, axis=2)
    column = header.x + LEFT_INSET
    rows = np.nonzero(painted[:, column])[0]
    rows = rows[rows > header.y]
    assert rows.size, f"no popup stands under the header at {header}"
    columns = np.nonzero(painted[rows, column:].any(axis=0))[0]
    return int(columns.max()) + column


@pytest.fixture
def startup() -> Startup:
    return Startup(reconstruction=PLAYABLE_RECONSTRUCTION, project=ARRANGED_PROJECT)


class TestMenuPopupsHoldTheirWidth:
    """Every menu popup keeps its width on every frame it stands open."""

    def test_each_popup_stands_still(self, screen: Screen) -> None:
        background = token_color(shipped_palettes().get(DEFAULT_PALETTE_NAME), POPUP_TOKEN)

        def measuring(group: MenuElements) -> None:
            screen.menu.open(group)
            screen.frames(OPENING_FRAMES)
            header = screen.menu.header(group)
            edges: List[int] = []
            for _ in range(READINGS):
                edges.append(popup_right_edge(screen.frame_pixels(), header, background))
                screen.frames(FRAMES_BETWEEN_READINGS)

            assert len(set(edges)) == 1, f"the {group} popup widened: {edges}"
            screen.menu.close()
            screen.frames(OPENING_FRAMES)

        def open_each_menu(screen: Screen) -> None:
            for group in MENUS:
                measuring(group)

        screen.scenario(open_each_menu).run()


class TestPrintedKeysFollowTheScheme:
    """Each menu entry prints the keys the scheme in place gives the action it runs."""

    def test_each_entry_prints_its_keys(self, screen: Screen) -> None:
        for group, item, shortcut_id in PRINTED:
            entries = {entry.label: entry.keys for entry in screen.menu.entries(group)}
            assert screen.menu.label(item) in entries, f"{group} offers no {item}: {list(entries)}"
            assert entries[screen.menu.label(item)] == screen.shortcut_words(shortcut_id), f"{item}"
