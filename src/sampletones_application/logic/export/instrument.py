from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Mapping, Protocol, Tuple

from sampletones_application.config.managers.session import SessionManager
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


def voice_instruments(voice: VoiceUnion) -> Tuple[InstrumentEntry, ...]:
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
    return tuple(voice_instrument_entries(voice, start_index=FIRST_INSTRUMENT_INDEX))


def voice_instrument(project: Project, entry: InstrumentEntry) -> ExportableInstrument:
    """One of a voice's instruments, ready to be given a destination.

    Args:
        project: The project the voice belongs to, which states the rate and the tuning.
        entry: The instrument being written.

    Returns:
        ExportableInstrument: The instrument and the name to suggest for it.

    Raises:
        ValueError: If the project's samples were reconstructed against tunings that differ.
    """
    return ExportableInstrument(name=entry.name, source=instrument_source(project, entry))


def instrument_source(project: Project, entry: InstrumentEntry) -> InstrumentSource:
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
        channel=entry.export_channel,
        features=entry.features,
        loop_point=entry.loop_point,
        nes_frequency=project.settings.nes_frequency,
        tuning=tuning_from_project(project),
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

    The destination carries the last two decisions: its extension names the format, and its stem
    names the instrument the file holds, so renaming a file in the save dialog renames what is
    written into it.
    """

    def __init__(
        self,
        session_manager: SessionManager,
        export_service: InstrumentExportServiceProtocol,
        export_backends: Dict[ExportFormat, ExportBackend],
    ) -> None:
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
