from dataclasses import dataclass
from pathlib import Path
from typing import AbstractSet, Final

from sampletones_application.config.managers.session import SessionManager
from sampletones_application.logic.export.nsf.protocol import NSFExportServiceProtocol
from sampletones_application.view_model.shared.nsf.offer import NO_FRAMES, NSFExportOffer
from sampletones_core.constants.enums import ChannelName
from sampletones_core.exports.backend import ExportBackend
from sampletones_core.exports.request import SampleExport
from sampletones_core.exports.scope import ExportScope
from sampletones_player.compression.scheme import offered_schemes
from sampletones_player.export.program import NSFProgram

NO_TICKS: Final[int] = 0


@dataclass(frozen=True)
class SampleSource:
    """A reconstruction's slices, written as a program sounding them together once through.

    Attributes:
        request: The slices the export writes.
    """

    request: SampleExport

    @property
    def scope(self) -> ExportScope:
        return ExportScope.SAMPLE

    @property
    def name(self) -> str:
        return self.request.name

    @property
    def nes_frequency(self) -> int:
        return self.request.nes_frequency

    def offer(self) -> NSFExportOffer:
        """The channels the slices sound on, and the schemes that write slices seeding no dictionary."""
        sounded = {instrument.channel for instrument in self.request.instruments}
        return NSFExportOffer(
            channels=tuple(channel for channel in ChannelName.items() if channel in sounded),
            frame_count=NO_FRAMES,
            schemes=offered_schemes(seeded=False),
        )

    def program(self) -> NSFProgram:
        return NSFProgram.for_sample(self.request)

    def ticks(self, channels: AbstractSet[ChannelName]) -> int:
        """The ticks the longest slice on ``channels`` runs for, which is how long the song lasts."""
        return max(
            (
                instrument.features.frame_count
                for instrument in self.request.instruments
                if instrument.channel in channels
            ),
            default=NO_TICKS,
        )

    def frame_tick(self, frame: int) -> int:
        """The tick order frame ``frame`` starts on.

        Raises:
            ValueError: Always, since a reconstruction plays its slices through once, laid out in
                no order frames.
        """
        raise ValueError(f"A reconstruction is laid out in no order frames, and frame {frame} was asked for")

    def proposed_directory(self, session_manager: SessionManager) -> Path:
        """The folder the last instrument was exported to."""
        return session_manager.get_instrument_path()

    def remember_directory(self, session_manager: SessionManager, directory: Path) -> None:
        """Opens the next instrument export where this one was written."""
        session_manager.set_instrument_path(directory)

    def submit(
        self,
        service: NSFExportServiceProtocol,
        destination: Path,
        backend: ExportBackend,
    ) -> None:
        service.export_sample(destination, backend, self.request)
