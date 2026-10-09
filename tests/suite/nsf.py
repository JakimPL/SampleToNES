from dataclasses import dataclass
from pathlib import Path
from typing import Final, List, Tuple
from unittest.mock import MagicMock

from sampletones_application.view_model.shared.nsf.choices import NSFExportChoices
from sampletones_application.view_model.shared.nsf.offer import FIRST_FRAME, NO_FRAMES, NSFExportOffer
from sampletones_application.view_model.shared.nsf.repeat import NSFRepeat
from sampletones_core.constants.enums import ChannelName
from sampletones_core.exports.backend import ExportBackend
from sampletones_core.exports.request import ProjectExport, SampleExport
from sampletones_core.exports.scope import ExportScope
from sampletones_player.compression.scheme import offered_schemes
from sampletones_player.export.program import NSFProgram
from sampletones_player.nsf.information import NSFInformation
from sampletones_shared.paths.extensions import EXT_FILE_NSF

ORDER_FRAMES: Final[int] = 12
SAMPLE_CHANNELS: Final[Tuple[ChannelName, ...]] = (ChannelName.PULSE1, ChannelName.TRIANGLE)
PROGRAM_TITLE: Final[str] = "Rainy Day Theme"
PROGRAM_ARTIST: Final[str] = "J. Kowalski"


def project_offer() -> NSFExportOffer:
    """What a project laid out in a dozen frames offers: every channel, frame and scheme."""
    return NSFExportOffer(
        channels=tuple(ChannelName.items()),
        frame_count=ORDER_FRAMES,
        schemes=offered_schemes(seeded=True),
    )


def sample_offer() -> NSFExportOffer:
    """What a reconstruction sounding two channels offers."""
    return NSFExportOffer(
        channels=SAMPLE_CHANNELS,
        frame_count=NO_FRAMES,
        schemes=offered_schemes(seeded=False),
    )


def standing_choices(offer: NSFExportOffer) -> NSFExportChoices:
    """Choices sounding every channel ``offer`` holds and repeating from the start."""
    return NSFExportChoices(
        information=NSFInformation(title=PROGRAM_TITLE, artist=PROGRAM_ARTIST),
        channels=frozenset(offer.channels),
        repeat=NSFRepeat.FROM_START,
        loop_frame=FIRST_FRAME,
        scheme=offer.schemes[-1],
    )


@dataclass(frozen=True)
class ProjectRun:
    destination: Path
    backend: ExportBackend
    request: ProjectExport


@dataclass(frozen=True)
class SampleRun:
    destination: Path
    backend: ExportBackend
    request: SampleExport


class FakeNSFExportService:
    """The export service as an NSF setup hands its run over, holding each run it was given."""

    def __init__(self) -> None:
        self.projects: List[ProjectRun] = []
        self.samples: List[SampleRun] = []

    def export_project(
        self,
        destination: Path,
        backend: ExportBackend,
        request: ProjectExport,
    ) -> None:
        self.projects.append(ProjectRun(destination=destination, backend=backend, request=request))

    def export_sample(
        self,
        destination: Path,
        backend: ExportBackend,
        request: SampleExport,
    ) -> None:
        self.samples.append(SampleRun(destination=destination, backend=backend, request=request))


class FakeProgramBackend:
    """The NSF backend as a setup binds it, holding each program chosen and the backend it gave."""

    def __init__(self) -> None:
        self.programs: List[NSFProgram] = []
        self.chosen: List[ExportBackend] = []

    @property
    def program(self) -> NSFProgram:
        assert self.programs, "A program was expected to be chosen"
        return self.programs[-1]

    def choosing(self, program: NSFProgram) -> ExportBackend:
        backend = MagicMock(spec=ExportBackend)
        self.programs.append(program)
        self.chosen.append(backend)
        return backend

    def extension(self, scope: ExportScope) -> str:  # pylint: disable=unused-argument
        return EXT_FILE_NSF
