from pathlib import Path
from typing import FrozenSet, Protocol

from sampletones_core.exports.artifact import ExportArtifact
from sampletones_core.exports.format import ExportFormat
from sampletones_core.exports.progress import SILENT_REPORTER, ExportReporter
from sampletones_core.exports.request import (
    InstrumentExport,
    ProjectExport,
    SampleExport,
)
from sampletones_core.exports.scope import ExportScope


class ExportBackend(Protocol):
    """Writes the application's work in one of the file formats it exports to.

    A backend owns both the byte layout and the shape each :class:`ExportScope` takes on
    disk, so a format that gathers a whole reconstruction into one document writes one
    where another writes a file per instrument. Every scope is written to a file path the
    caller chooses, and :meth:`extension` names the extension it carries.

    A write reports itself as it runs and asks its reporter whether the answer is still
    wanted, which is what lets a caller watch a long format and withdraw one. A caller with
    nothing to tell passes :data:`SILENT_REPORTER` and hears back the file alone.
    """

    @property
    def export_format(self) -> ExportFormat:
        """The format this backend writes."""

    @property
    def supported_scopes(self) -> FrozenSet[ExportScope]:
        """The scopes this format can express."""

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
        report: ExportReporter = SILENT_REPORTER,
    ) -> ExportArtifact:
        """Writes one channel slice.

        Args:
            destination: The file to write.
            request: The slice to write.
            report: Hears each stage of the write, and answers whether it goes on.

        Returns:
            ExportArtifact: The paths written and what the format's limits left out.

        Raises:
            OperationCancelled: If ``report`` withdraws the write.
            OSError: If the destination cannot be written.
        """

    def write_sample(
        self,
        destination: Path,
        request: SampleExport,
        report: ExportReporter = SILENT_REPORTER,
    ) -> ExportArtifact:
        """Writes every channel slice of one reconstruction.

        Args:
            destination: The file this scope is written to. A format that keeps one
                instrument per file writes its slices beside it, each named after the
                instrument it carries.
            request: The reconstruction's slices.
            report: Hears each stage of the write, and answers whether it goes on.

        Returns:
            ExportArtifact: The paths written and what the format's limits left out.

        Raises:
            OperationCancelled: If ``report`` withdraws the write.
            OSError: If the destination cannot be written.
        """

    def write_project(
        self,
        destination: Path,
        request: ProjectExport,
        report: ExportReporter = SILENT_REPORTER,
    ) -> ExportArtifact:
        """Writes a whole composition.

        Args:
            destination: The file to write.
            request: The project to write.
            report: Hears each stage of the write, and answers whether it goes on.

        Returns:
            ExportArtifact: The paths written and what the format's limits left out.

        Raises:
            OperationCancelled: If ``report`` withdraws the write.
            OSError: If the destination cannot be written.
            ValueError: If the project holds more than the format has room for.
        """
