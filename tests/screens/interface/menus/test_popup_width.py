from typing import Final, List, Tuple

import numpy as np

from sampletones_application.categories.elements.global_ import MenuElements
from sampletones_application.utils.palette.catalog import DEFAULT_PALETTE_NAME
from tests.suite.screens.dearpygui.geometry import Point
from tests.suite.screens.palettes import Color, shipped_palettes, token_color
from tests.suite.screens.screen import Screen

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


class TestMenuPopupsHoldTheirWidth:
    """Every menu popup keeps its width on every frame it stands open.

    The scenario opens each menu, reads the popup's right edge on several frames, and expects one
    value.
    """

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
