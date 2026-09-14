from dataclasses import dataclass
from pathlib import Path
from typing import AbstractSet

from sampletones_application.config.managers.session import SessionManager
from sampletones_application.logic.export.nsf.protocol import NSFExportServiceProtocol
from sampletones_application.view_model.shared.nsf.offer import NSFExportOffer
from sampletones_core.constants.enums import ChannelName
from sampletones_core.exports.backend import ExportBackend
from sampletones_core.exports.request import ProjectExport
from sampletones_core.exports.scope import ExportScope
from sampletones_core.timing import SongTiming
from sampletones_player.compression.scheme import offered_schemes
from sampletones_player.export.program import NSFProgram
from sampletones_shared.utils.system.paths import get_directory


@dataclass(frozen=True)
class ProjectSource:
    """The open project, written as a program playing its whole song.

    Attributes:
        request: The project the export writes.
        name: The name the project is known by, which the proposed file carries.
    """

    request: ProjectExport
    name: str

    @property
    def scope(self) -> ExportScope:
        return ExportScope.PROJECT

    @property
    def nes_frequency(self) -> int:
        return self.request.project.settings.nes_frequency

    def offer(self) -> NSFExportOffer:
        """Every channel, the frames of the order, and every scheme, the samples seeding the dictionary."""
        return NSFExportOffer(
            channels=tuple(ChannelName.items()),
            frame_count=self.request.project.song.order_length(),
            schemes=offered_schemes(seeded=True),
        )

    def program(self) -> NSFProgram:
        return NSFProgram.for_project(self.request.project)

    def ticks(self, channels: AbstractSet[ChannelName]) -> int:  # pylint: disable=unused-argument
        """The ticks the whole order plays for, which every channel shares."""
        project = self.request.project
        return SongTiming.from_project(project).frame_tick(project.song.order_length())

    def frame_tick(self, frame: int) -> int:
        """The tick order frame ``frame`` starts on, under the groove the song plays at."""
        return SongTiming.from_project(self.request.project).frame_tick(frame)

    def proposed_directory(self, session_manager: SessionManager) -> Path:
        """The folder the project was last opened or saved in."""
        return get_directory(session_manager.get_project_path())

    def remember_directory(  # pylint: disable=unused-argument
        self,
        session_manager: SessionManager,
        directory: Path,
    ) -> None:
        """Keeps the project's folder where opening and saving the project set it."""

    def submit(
        self,
        service: NSFExportServiceProtocol,
        destination: Path,
        backend: ExportBackend,
    ) -> None:
        service.export_project(destination, backend, self.request)
