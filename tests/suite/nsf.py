from dataclasses import dataclass
from pathlib import Path
from typing import Final, List, Tuple
from unittest.mock import MagicMock

from sampletones_application.view_model.shared.nsf.choices import NSFExportChoices
from sampletones_application.view_model.shared.nsf.offer import FIRST_FRAME, NO_FRAMES, NSFExportOffer
from sampletones_application.view_model.shared.nsf.repeat import NSFRepeat
from sampletones_core.constants.enums import ChannelName
from sampletones_core.exports.backend import ExportBackend
from sampletones_core.exports.format import ExportFormat
from sampletones_core.exports.request import ProjectExport, SampleExport
from sampletones_core.exports.scope import ExportScope
from sampletones_player.compression.scheme import offered_schemes
from sampletones_player.export.program import Program
from sampletones_player.information import ProgramInformation, ProgramText, TextLine
from sampletones_player.nsf.header import HEADER_TEXT
from sampletones_shared.paths.extensions import EXT_FILE_NSF

ORDER_FRAMES: Final[int] = 12
SAMPLE_CHANNELS: Final[Tuple[ChannelName, ...]] = (ChannelName.PULSE1, ChannelName.TRIANGLE)
PROGRAM_TITLE: Final[str] = "Rainy Day Theme"
PROGRAM_ARTIST: Final[str] = "J. Kowalski"
OTHER_FORMAT: Final[ExportFormat] = ExportFormat.BITPHASE
OTHER_EXTENSION: Final[str] = ".prg"
NARROW_TEXT: Final[ProgramText] = ProgramText(
    title=TextLine(encoding="ascii", room=2, folded=True),
    artist=TextLine(encoding="ascii", room=3, folded=True),
    copyright=TextLine(encoding="ascii", room=4, folded=True),
)


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
        information=ProgramInformation(title=PROGRAM_TITLE, artist=PROGRAM_ARTIST),
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
    """A program backend as a setup binds it, holding each program chosen and the backend it gave.

    Attributes:
        export_format: The format the backend stands for.
        text: The room each of a program's lines of text has in its files.
    """

    def __init__(
        self,
        export_format: ExportFormat,
        file_extension: str,
        text: ProgramText,
    ) -> None:
        self.export_format = export_format
        self.text = text
        self._file_extension = file_extension
        self.programs: List[Program] = []
        self.chosen: List[ExportBackend] = []

    @property
    def program(self) -> Program:
        assert self.programs, "A program was expected to be chosen"
        return self.programs[-1]

    def choosing(self, program: Program) -> ExportBackend:
        backend = MagicMock(spec=ExportBackend)
        self.programs.append(program)
        self.chosen.append(backend)
        return backend

    def extension(self, scope: ExportScope) -> str:  # pylint: disable=unused-argument
        return self._file_extension


def nsf_backend() -> FakeProgramBackend:
    """A backend standing for the NSF format, its files and the room their header gives the text."""
    return FakeProgramBackend(ExportFormat.NSF, EXT_FILE_NSF, HEADER_TEXT)


def other_backend() -> FakeProgramBackend:
    """A backend standing for a second kind of program file, with an extension and a narrow line
    of text of its own for each line, so a setup is seen to follow the format it was opened for."""
    return FakeProgramBackend(OTHER_FORMAT, OTHER_EXTENSION, NARROW_TEXT)
