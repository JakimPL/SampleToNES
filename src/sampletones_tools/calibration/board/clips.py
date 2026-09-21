from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from shutil import copyfile
from typing import Protocol, Sequence

from .layout import AUDIO_DIRECTORY, PAGE_DIRECTORY
from .reading import RunReading


class ClipStore(Protocol):
    """Where the page finds a clip, told as a reference relative to the page itself."""

    def href(self, run: RunReading, source: Path) -> str: ...


@dataclass(frozen=True)
class InPlaceClips:
    """Clips the page reaches where the run already wrote them.

    A page written into its own run stands beside the renders and the recordings it plays, so it
    names them as they lie and the run grows by the page alone.
    """

    def href(self, run: RunReading, source: Path) -> str:
        """The run's own clip, named relative to the run directory the page sits in."""
        return PurePosixPath(source.relative_to(run.directory)).as_posix()


@dataclass(frozen=True)
class GatheredClips:
    """Clips the page carries with it, copied under its own directory.

    A page comparing runs lies apart from all of them, so each clip it plays is brought along and
    the page moves as one folder.

    Attributes:
        output: The directory the page is written into.
    """

    output: Path

    def href(self, run: RunReading, source: Path) -> str:
        """The clip's copy under the page's audio directory, named relative to the page."""
        relative = PurePosixPath(PAGE_DIRECTORY, AUDIO_DIRECTORY, run.label, *source.relative_to(run.directory).parts)
        destination = self.output / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        copyfile(source, destination)
        return relative.as_posix()


def clip_store(runs: Sequence[RunReading], output: Path) -> ClipStore:
    """
    The store a page built over these runs into this directory plays from.

    A page written into the one run it reports plays that run's files where they lie; a page
    written anywhere else carries copies, so either page opens from the folder it was written into.

    Args:
        runs: The runs the page reports.
        output: The directory the page is written into.

    Returns:
        The store the page's references come from.
    """
    if len(runs) == 1 and runs[0].directory.resolve() == output.resolve():
        return InPlaceClips()

    return GatheredClips(output=output)
