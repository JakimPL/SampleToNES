from pathlib import Path
from typing import Final

import pytest

from assets.footage.filming import Filming
from assets.footage.shoot import Take
from assets.footage.shot import ground
from automation.palettes import worn_palette
from automation.screen import Screen
from automation.worlds.home import World

FILMING_SECONDS: Final[float] = 3600.0


class ReelFootage:
    """The Reconstructions tab filmed through a timeline of listenings, one tick of the playhead a frame."""

    @pytest.mark.screen_timeout(FILMING_SECONDS)
    def footage_reel(self, screen: Screen, take: Take, document: Path, world: World) -> None:
        Filming(screen, take, ground(worn_palette(world))).film(document)
