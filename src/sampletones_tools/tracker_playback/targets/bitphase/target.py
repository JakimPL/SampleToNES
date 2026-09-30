from dataclasses import dataclass
from pathlib import Path
from typing import Final, Self

from sampletones_core.formats.bitphase.btp import write_btp
from sampletones_core.formats.bitphase.builder import build_bitphase
from sampletones_core.project.project import Project
from sampletones_shared.paths.extensions import EXT_FILE_BITPHASE, EXT_FILE_JSON
from sampletones_tools.tracker_playback.targets.bitphase.engine import BitphaseEngine
from sampletones_tools.tracker_playback.targets.protocol import TargetPlayback

TITLE: Final[str] = "Bitphase"
PLAYER: Final[str] = "the engine of the Bitphase checkout at `{root}`"


@dataclass(frozen=True)
class BitphaseTarget:
    """Bitphase as a playback target: a project exported to a `.btp` document and played by Bitphase's engine.

    Attributes:
        engine: The engine of the checkout that plays the documents.
    """

    engine: BitphaseEngine

    @classmethod
    def located(cls, root: Path) -> Self:
        """The target playing documents with the engine of the checkout at ``root``.

        Args:
            root: The Bitphase checkout's top directory.

        Returns:
            Self: The target.

        Raises:
            EngineError: If node is absent, or the checkout lacks a file the trace loads.
        """
        return cls(engine=BitphaseEngine.located(root))

    @property
    def title(self) -> str:
        """The tracker's name, as the report prints it."""
        return TITLE

    @property
    def player(self) -> str:
        """The checkout whose engine plays the documents, as the report introduces it."""
        return PLAYER.format(root=self.engine.checkout.root)

    def play(
        self,
        project: Project,
        directory: Path,
        name: str,
    ) -> TargetPlayback:
        """Exports a project to a `.btp` document, plays it with Bitphase's engine and reads every tick.

        The document is built by the exporter the application's Bitphase export runs, and the trace the
        engine writes is kept beside it.

        Args:
            project: The project to export and play.
            directory: Where the document and its trace are written.
            name: The stem both files are written under.

        Returns:
            TargetPlayback: The document, what Bitphase played of it, and what the export left out.

        Raises:
            EngineError: If Bitphase fails to play the document.
        """
        built = build_bitphase(project)
        document = directory / f"{name}{EXT_FILE_BITPHASE}"
        write_btp(
            document,
            built.document,
        )
        return TargetPlayback(
            document=document,
            trace=self.engine.trace(
                document,
                directory / f"{name}{EXT_FILE_JSON}",
            ),
            skipped_rows=len(built.skipped_rows),
            truncation=built.truncation,
        )
