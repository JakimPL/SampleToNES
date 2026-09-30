from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Protocol

from sampletones_core.exporters.truncation import EnvelopeTruncation
from sampletones_core.project.project import Project
from sampletones_shared.exceptions import SampleToNESError
from sampletones_tools.tracker_playback.trace.sound import SongTrace


class PlaybackError(SampleToNESError):
    """A target could not play a project: the tracker or what runs it is missing, or the run failed."""


@dataclass(frozen=True)
class TargetPlayback:
    """What a target made of one project, and what every channel sounded when the tracker played it.

    Attributes:
        document: The file the export wrote, which the tracker played.
        trace: What each channel sounded on every engine tick, read as the registers the chip takes.
        skipped_rows: How many rows the export wrote as note cuts for lack of an instrument.
        truncation: The instruments the format's value limit shortened, or ``None`` where every one fit.
    """

    document: Path
    trace: SongTrace
    skipped_rows: int
    truncation: Optional[EnvelopeTruncation]


class PlaybackTarget(Protocol):
    """A tracker a project is exported to and played by, so what it plays can be held against the app.

    Each tracker is one implementation. It exports the project with the application's own exporter,
    plays the file with the tracker's own playback code, and reads what every channel sounds on every
    tick into a ``SongTrace``, whatever produced those ticks.
    """

    @property
    def title(self) -> str:
        """The tracker's name, as the report prints it."""

    @property
    def player(self) -> str:
        """What plays the exported files, as the report introduces it."""

    def play(
        self,
        project: Project,
        directory: Path,
        name: str,
    ) -> TargetPlayback:
        """Exports a project, plays the file with the tracker, and reads every tick of every channel.

        Args:
            project: The project to export and play.
            directory: Where the exported file and whatever its playing writes are kept.
            name: The stem every file of this project is written under.

        Returns:
            TargetPlayback: The file exported, what it played, and what the export left out.

        Raises:
            PlaybackError: If the tracker fails to play the file.
        """
