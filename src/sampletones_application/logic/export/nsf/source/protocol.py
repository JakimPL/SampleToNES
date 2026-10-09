from pathlib import Path
from typing import AbstractSet, Protocol

from sampletones_application.config.managers.session import SessionManager
from sampletones_application.logic.export.nsf.protocol import NSFExportServiceProtocol
from sampletones_application.view_model.shared.nsf.offer import NSFExportOffer
from sampletones_core.constants.enums import ChannelName
from sampletones_core.exports.backend import ExportBackend
from sampletones_core.exports.scope import ExportScope
from sampletones_player.export.program import NSFProgram


class NSFExportSource(Protocol):
    """What an NSF export writes, answering every question the setup asks of it.

    A whole project and a reconstruction's slices reach a program through the same dialog, and
    each states for itself what that dialog offers, what the export writes on its own, how long
    the song runs, the tick each order frame starts on and which run of the service writes it.
    """

    @property
    def scope(self) -> ExportScope: ...

    @property
    def name(self) -> str: ...

    @property
    def nes_frequency(self) -> int: ...

    def offer(self) -> NSFExportOffer: ...

    def program(self) -> NSFProgram: ...

    def ticks(self, channels: AbstractSet[ChannelName]) -> int: ...

    def frame_tick(self, frame: int) -> int: ...

    def proposed_directory(self, session_manager: SessionManager) -> Path: ...

    def remember_directory(self, session_manager: SessionManager, directory: Path) -> None: ...

    def submit(
        self,
        service: NSFExportServiceProtocol,
        destination: Path,
        backend: ExportBackend,
    ) -> None: ...
