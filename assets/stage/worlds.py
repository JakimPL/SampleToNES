import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Final, Tuple

from assets.demo.paths import (
    LIBRARY_FOLDER,
    PROJECTS_FOLDER,
    RECONSTRUCTIONS_FOLDER,
    RECORDINGS_FOLDER,
)
from assets.stage.paths import DEMO_DIRECTORY
from automation.worlds.home import HomeFile, World, one_worker_config
from sampletones_application.config.session.application.config import (
    ApplicationConfig,
)
from sampletones_application.config.session.application.display import (
    DisplayConfig,
)
from sampletones_application.config.session.state.paths import LastPaths
from sampletones_application.config.session.state.state import ApplicationState
from sampletones_application.config.session.state.window import ViewportState
from sampletones_shared.paths.user import USER_PATH_DOCUMENTS

DOCUMENT_FOLDERS: Final[tuple[str, ...]] = (
    LIBRARY_FOLDER,
    RECONSTRUCTIONS_FOLDER,
    PROJECTS_FOLDER,
)


class MissingDemoError(FileNotFoundError):
    """Raised when the demo tree a maker films has not been made."""


@dataclass(frozen=True)
class DemoTree:
    """The demo tree laid into a home: the recordings beside the working directory, the documents in the
    documents folder.

    The reconstructions name their recordings relative to the tree, so the recordings go where the
    application resolves a relative path from, its working directory, and the documents go where the
    application keeps them.

    Attributes:
        source: The tree the demo maker wrote.
        working_directory: Where the application is started, which the recordings folder is laid beside.
        documents: The application's documents folder, which takes the library, the reconstructions
            and the projects.
    """

    source: Path
    working_directory: Path
    documents: Path

    def write(self) -> None:
        """Copies the tree into place.

        Raises:
            MissingDemoError: If the source holds no tree.
        """
        if not (self.source / RECORDINGS_FOLDER).is_dir():
            raise MissingDemoError(f"No demo tree at {self.source}; make demo writes one")

        shutil.copytree(
            self.source / RECORDINGS_FOLDER,
            self.working_directory / RECORDINGS_FOLDER,
            dirs_exist_ok=True,
        )
        for folder in DOCUMENT_FOLDERS:
            shutil.copytree(
                self.source / folder,
                self.documents / folder,
                dirs_exist_ok=True,
            )


def demo_tree() -> DemoTree:
    """The demo tree laid beside the working directory the application is started in and into its documents."""
    return DemoTree(source=DEMO_DIRECTORY, working_directory=Path.cwd(), documents=USER_PATH_DOCUMENTS)


def stage_world(
    viewport: ViewportState,
    *,
    collapsed_cards: Dict[str, bool],
    files: Tuple[HomeFile, ...],
) -> World:
    """A home holding ``files``, opening a window of ``viewport`` with the cards ``collapsed_cards`` folds and the
    frame-rate reading off.

    The session remembers the documents folder as where audio was last written, so a window proposing
    a file for a render names a place under the documents.
    """
    return World(
        state=ApplicationState(
            viewport=viewport,
            last_paths=LastPaths(audio=USER_PATH_DOCUMENTS),
            collapsed_cards=collapsed_cards,
        ),
        application_config=ApplicationConfig(display=DisplayConfig(show_frame_rate=False)),
        config=one_worker_config(),
        files=files,
    )


def demo_world(viewport: ViewportState) -> World:
    """A home holding the demo tree, opening a window of ``viewport`` with every card open."""
    return stage_world(viewport, collapsed_cards={}, files=(demo_tree(),))
