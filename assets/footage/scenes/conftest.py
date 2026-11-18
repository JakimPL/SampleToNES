import os
from pathlib import Path

import pytest

from assets.footage.shoot import Take, handed_take
from assets.footage.shot import COLLAPSED_CARDS, VIEWPORT
from assets.stage.demo import piece_document
from assets.stage.worlds import demo_tree, stage_world
from automation.application.startup import Startup
from automation.worlds.home import World


@pytest.fixture(name="take")
def take_fixture() -> Take:
    """The take the footage maker handed over."""
    return handed_take(os.environ)


@pytest.fixture(name="document")
def document_fixture(take: Take) -> Path:
    """The reconstruction filmed: the take's own, or the demo piece in the scene's home."""
    return piece_document() if take.shoot.document is None else take.shoot.document


@pytest.fixture(name="world")
def world_fixture(take: Take) -> World:
    """A home opening the window the shot is framed in, holding the demo tree where the demo piece is filmed."""
    files = (demo_tree(),) if take.shoot.document is None else ()
    return stage_world(VIEWPORT, collapsed_cards=COLLAPSED_CARDS, files=files)


@pytest.fixture(name="startup")
def startup_fixture(document: Path) -> Startup:
    """The filmed reconstruction open at start, with no project."""
    return Startup(reconstruction=document, project=None)
