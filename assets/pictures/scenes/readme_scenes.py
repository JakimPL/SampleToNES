from typing import Final

import pytest

from assets.pictures.demo import piece_document
from assets.pictures.paths import README_PICTURE
from assets.pictures.worlds import README_VIEWPORT, demo_world
from assets.pictures.writer import Pictures
from automation.screen import Screen
from automation.steps.reconstructions import expect_open, load_from_the_browser
from automation.worlds.home import World
from sampletones_core.constants.enums import ChannelName

WAVEFORM_POINT: Final[float] = 0.6
SETTLE_FRAMES: Final[int] = 10


class ReadmeScenes:
    """The picture the README opens with: the piece open on the Reconstruction tab, its stems with their levels
    folded away so every recording shows, its instruments beside the waveform, and the pointer resting on the
    waveform so the status bar reads its hint.
    """

    @pytest.fixture(name="world")
    def world_fixture(self) -> World:
        """A home holding the demo tree, at the window size the README shows at half scale."""
        return demo_world(README_VIEWPORT)

    def picture_window(self, screen: Screen, pictures: Pictures) -> None:
        document = piece_document()
        load_from_the_browser(screen, document)
        expect_open(screen, document)
        screen.reconstructions.instruments.bring_forward(ChannelName.PULSE1)
        screen.reconstructions.stems.toggle_levels()
        screen.expect(
            screen.reconstructions.stems.levels_collapsed,
            bool,
            description="the levels collapsed",
        )
        screen.hand.move_to(screen.reconstructions.waveform.point(WAVEFORM_POINT))
        screen.frames(SETTLE_FRAMES)

        pictures.window(README_PICTURE)
