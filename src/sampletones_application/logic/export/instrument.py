# TODO: refactor into a subpackage

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Mapping, Optional, Protocol, Tuple

from sampletones_application.config.managers.session import SessionManager
from sampletones_application.constants.instruments import INSTRUMENT_CHANNEL
from sampletones_application.logic.project.controller import ProjectController
from sampletones_core.constants.enums import ChannelName
from sampletones_core.exporters.slices import (
    FIRST_INSTRUMENT_INDEX,
    InstrumentEntry,
    voice_instrument_entries,
)
from sampletones_core.exports.backend import ExportBackend
from sampletones_core.exports.extensions import format_for_extension
from sampletones_core.exports.format import ExportFormat
from sampletones_core.exports.request import InstrumentExport, InstrumentSource
from sampletones_core.exports.scope import ExportScope
from sampletones_core.project.project import Project
from sampletones_core.project.tuning import tuning_from_project
from sampletones_core.project.voices.voice import VoiceUnion


@dataclass(frozen=True)
class ExportableInstrument:
    """One instrument ready to be asked for a destination.

    Attributes:
        name: The name the save dialog suggests, which the written instrument keeps unless the
            reader renames the file.
        source: The instrument itself, awaiting the name its destination gives it.
    """

    name: str
    source: InstrumentSource


def voice_entries(voice: VoiceUnion) -> Tuple[InstrumentEntry, ...]:
    """The instruments one voice offers to an export.

    A module writing every voice and a file writing one read the same rule, so a reader is offered
    exactly the instruments a module would have held: a sample yields one per channel its
    reconstruction found frames for, and a voice written by hand yields the single set of envelopes
    every channel reads.

    Args:
        voice: The voice whose instruments are offered.

    Returns:
        Tuple[InstrumentEntry, ...]: Its instruments, in channel order.
    """
    return tuple(
        voice_instrument_entries(voice, start_index=FIRST_INSTRUMENT_INDEX),
    )


def sounding_channel(entry: InstrumentEntry) -> ChannelName:
    """The channel a file holding one instrument alone sounds it on.

    A sample's slice states the channel it was reconstructed for, and that is the channel it is
    sounded on. A voice written by hand states one set of envelopes for no channel in particular,
    and a file must still play it somewhere, so it is sounded where the app reads it: the channel
    its own editor shows it under, whose reference is the tonal root its envelopes are measured
    against.

    Args:
        entry: The instrument being written.

    Returns:
        ChannelName: The channel the written file plays the instrument through.
    """
    if entry.channel is None:
        return INSTRUMENT_CHANNEL

    return entry.channel


def instrument_source(
    project: Project,
    entry: InstrumentEntry,
) -> InstrumentSource:
    """One of a voice's instruments, measured at the rate and tuning its project plays it at.

    Args:
        project: The project the voice belongs to, which states the rate and the tuning.
        entry: The instrument being written.

    Returns:
        InstrumentSource: The instrument, awaiting the name its destination gives it.

    Raises:
        ValueError: If the project's samples were reconstructed against tunings that differ.
    """
    return InstrumentSource(
        channel=sounding_channel(entry),
        features=entry.features,
        loop_point=entry.loop_point,
        nes_frequency=project.settings.nes_frequency,
        tuning=tuning_from_project(project),
    )


def exportable_instrument(
    project: Project,
    entry: InstrumentEntry,
) -> ExportableInstrument:
    """One of a voice's instruments, ready to be given a destination.

    Args:
        project: The project the voice belongs to, which states the rate and the tuning.
        entry: The instrument being written.

    Returns:
        ExportableInstrument: The instrument and the name to suggest for it.

    Raises:
        ValueError: If the project's samples were reconstructed against tunings that differ.
    """
    return ExportableInstrument(
        name=entry.name,
        source=instrument_source(project, entry),
    )


class InstrumentExportServiceProtocol(Protocol):
    """The slice of the export service one instrument's export drives.

    Typing the collaborator structurally keeps the logic layer independent of the service
    implementation; the composition root supplies the real service.
    """

    def export_instrument(
        self,
        destination: Path,
        backend: ExportBackend,
        request: InstrumentExport,
    ) -> None: ...


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

        A sample answers with the channels its reconstruction found frames for; a voice written by
        hand answers with a single ``None``, since its one set of envelopes belongs to no channel
        in particular. A menu reads this to decide whether it offers an item or a choice of
        channels, and hands one entry back to :meth:`voice_instrument`.

        Args:
            voice_id: The voice whose instruments are offered.

        Returns:
            Tuple[Optional[ChannelName], ...]: One entry per instrument the voice holds, empty
            while the pool holds no such voice or the voice writes nothing.
        """
        voice = self._controller.project.voices.get(voice_id)
        if voice is None:
            return ()

        return tuple(entry.channel for entry in voice_entries(voice))

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
        project = self._controller.project
        voice = project.voices.get(voice_id)
        if voice is None:
            return None

        entry = next(
            (candidate for candidate in voice_entries(voice) if candidate.channel == channel_name),
            None,
        )
        if entry is None:
            return None

        return exportable_instrument(project, entry)

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
