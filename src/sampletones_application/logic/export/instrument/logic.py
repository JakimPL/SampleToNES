from pathlib import Path
from typing import Dict, Mapping, Optional, Tuple

from sampletones_application.config.managers.session import SessionManager
from sampletones_application.logic.export.instrument.protocol import (
    InstrumentExportServiceProtocol,
)
from sampletones_application.logic.export.instrument.source import (
    ExportableInstrument,
    voice_instrument,
    voice_instrument_channels,
)
from sampletones_application.logic.project.controller import ProjectController
from sampletones_core.constants.enums import ChannelName
from sampletones_core.exports.backend import ExportBackend
from sampletones_core.exports.extensions import format_for_extension
from sampletones_core.exports.format import ExportFormat
from sampletones_core.exports.request import InstrumentSource
from sampletones_core.exports.scope import ExportScope


class InstrumentExportLogic:
    """The one way an instrument reaches a file, whichever surface asked for one.

    An instrument export is a set of envelopes, the channel they are read for and the rate they
    advance at. What produced them — a channel of the open reconstruction, a channel of a project
    sample, or a voice written by hand — is settled before anything here, so every surface answers
    with an :class:`InstrumentSource` and reaches the same write.

    A voice in the pool is answered for here as well, so a menu asks what one offers and a click
    asks for one of them by the channel it names, and both the sequencer's voice menu and the
    Reconstructions tab's export button write the same file for the same voice.

    The destination carries the last two decisions: its extension names the format, and its stem
    names the instrument the file holds, so renaming a file in the save dialog renames what is
    written into it.
    """

    def __init__(
        self,
        project_controller: ProjectController,
        session_manager: SessionManager,
        export_service: InstrumentExportServiceProtocol,
        export_backends: Dict[ExportFormat, ExportBackend],
    ) -> None:
        self._controller = project_controller
        self._session_manager = session_manager
        self._export_service = export_service
        self._export_backends = export_backends

    @property
    def backends(self) -> Mapping[ExportFormat, ExportBackend]:
        """Every backend an instrument can be written through, keyed by its format."""
        return self._export_backends

    @property
    def suggested_directory(self) -> Path:
        """The folder the save dialog opens on, which is where the last instrument landed."""
        return self._session_manager.get_instrument_path()

    def voice_instruments(self, voice_id: str) -> Tuple[Optional[ChannelName], ...]:
        """What one voice offers to an export, each named by the channel it is stated for.

        A menu reads this to decide whether it offers an item or a choice of channels, and hands
        one entry back to :meth:`voice_instrument`.

        Args:
            voice_id: The voice whose instruments are offered.

        Returns:
            Tuple[Optional[ChannelName], ...]: One entry per instrument the voice holds, empty
            while the pool holds no such voice or the voice writes nothing.
        """
        return voice_instrument_channels(self._controller.project, voice_id)

    def voice_instrument(
        self,
        voice_id: str,
        channel_name: Optional[ChannelName],
    ) -> Optional[ExportableInstrument]:
        """One of a voice's instruments, ready to be given a destination.

        Args:
            voice_id: The voice the instrument belongs to.
            channel_name: The channel the instrument is stated for, as
                :meth:`voice_instruments` named it.

        Returns:
            Optional[ExportableInstrument]: The instrument and the name to suggest for it, or
            ``None`` where the voice holds no instrument answering to that channel.

        Raises:
            ValueError: If the project's samples were reconstructed against tunings that differ.
        """
        return voice_instrument(self._controller.project, voice_id, channel_name)

    def export(self, destination: Path, source: InstrumentSource) -> None:
        """Writes one instrument to ``destination``, in the format its extension names.

        Args:
            destination: The file the save dialog was confirmed with.
            source: The instrument to write, awaiting the name the destination gives it.

        Raises:
            ValueError: If no format writing a single instrument claims the destination's
                extension, which a dialog offering those formats alone never yields.
        """
        export_format = self._format(destination)
        self._session_manager.set_instrument_path(destination.parent)
        self._export_service.export_instrument(
            destination,
            self._export_backends[export_format],
            source.named(destination.stem),
        )

    def _format(self, destination: Path) -> ExportFormat:
        export_format = format_for_extension(
            self._export_backends,
            ExportScope.INSTRUMENT,
            destination.suffix,
        )
        if export_format is None:
            raise ValueError(f"No export format writes '{destination.suffix}' for an instrument export")

        return export_format
