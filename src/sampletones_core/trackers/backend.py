from pathlib import Path
from typing import FrozenSet, Protocol

from sampletones_core.trackers.artifact import ExportArtifact
from sampletones_core.trackers.format import TrackerFormat
from sampletones_core.trackers.request import (
    InstrumentExport,
    ProjectExport,
    SampleExport,
)
from sampletones_core.trackers.scope import DestinationKind, ExportScope


class TrackerBackend(Protocol):
    """Writes the application's work in the file format one tracker reads.

    A backend owns both the byte layout and the shape each :class:`ExportScope` takes on
    disk, so a format that reads a whole reconstruction from a single file writes one
    where another writes a directory of per-instrument files. Callers ask
    :meth:`destination_kind` what to prompt for and hand the answer straight back as the
    ``destination``.
    """

    @property
    def tracker_format(self) -> TrackerFormat:
        """The format this backend writes."""

    @property
    def supported_scopes(self) -> FrozenSet[ExportScope]:
        """The scopes this format can express."""

    def destination_kind(self, scope: ExportScope) -> DestinationKind:
        """Whether ``scope`` is written to a file or into a directory.

        Args:
            scope: The scope about to be exported.

        Returns:
            DestinationKind: What the caller should prompt the user for.
        """

    def extension(self, scope: ExportScope) -> str:
        """The extension the files of ``scope`` carry, leading dot included.

        Args:
            scope: The scope about to be exported.

        Returns:
            str: The extension of each file the run writes.
        """

    def write_instrument(
        self,
        destination: Path,
        request: InstrumentExport,
    ) -> ExportArtifact:
        """Writes one generator slice.

        Args:
            destination: The file to write.
            request: The slice to write.

        Returns:
            ExportArtifact: The paths written and what the format's limits left out.

        Raises:
            OSError: If the destination cannot be written.
        """

    def write_sample(
        self,
        destination: Path,
        request: SampleExport,
    ) -> ExportArtifact:
        """Writes every generator slice of one reconstruction.

        Args:
            destination: The file to write, or the directory to fill.
            request: The reconstruction's slices.

        Returns:
            ExportArtifact: The paths written and what the format's limits left out.

        Raises:
            OSError: If the destination cannot be written.
        """

    def write_project(
        self,
        destination: Path,
        request: ProjectExport,
    ) -> ExportArtifact:
        """Writes a whole composition.

        Args:
            destination: The file to write.
            request: The project to write.

        Returns:
            ExportArtifact: The paths written and what the format's limits left out.

        Raises:
            OSError: If the destination cannot be written.
            ValueError: If the project holds more than the format has room for.
        """
