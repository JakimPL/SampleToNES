from pathlib import Path
from typing import Final, List, Tuple

from sampletones_core.project.project import Project
from sampletones_tools.tracker_playback.targets.protocol import TargetPlayback
from sampletones_tools.tracker_playback.trace.application import application_trace

REPLAYING_TITLE: Final[str] = "Replay"
REPLAYING_PLAYER: Final[str] = "the application itself"
REPLAYED_EXTENSION: Final[str] = ".txt"


class ReplayingTarget:
    """A playback target that plays every project back exactly as the application plays it.

    It writes a stand-in file per project and records what it was asked to play, so a case checks the
    run around a target without any tracker installed.
    """

    title: str = REPLAYING_TITLE
    player: str = REPLAYING_PLAYER

    def __init__(self) -> None:
        self.played: List[Tuple[Path, str]] = []

    def play(
        self,
        project: Project,
        directory: Path,
        name: str,
    ) -> TargetPlayback:
        self.played.append((directory, name))
        document = directory / f"{name}{REPLAYED_EXTENSION}"
        document.write_text(name, encoding="utf-8")
        return TargetPlayback(
            document=document,
            trace=application_trace(project),
            skipped_rows=0,
            truncation=None,
        )
