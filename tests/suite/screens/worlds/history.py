from pathlib import Path
from typing import Final

from sampletones_shared.paths.user import PROJECTS_DIRECTORY
from tests.suite.screens.seeds.projects import EveryPartProject
from tests.suite.screens.worlds.home import World, screen_filling_state

HISTORY_PROJECT: Final[Path] = PROJECTS_DIRECTORY / "History.stp"


def history_world() -> World:
    """A home holding :data:`HISTORY_PROJECT`, the project with something in every part a gesture reaches."""
    return World(
        state=screen_filling_state(),
        application_config=None,
        config=None,
        files=(EveryPartProject(HISTORY_PROJECT),),
    )
