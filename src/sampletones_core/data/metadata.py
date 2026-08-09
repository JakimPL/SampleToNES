from __future__ import annotations

from dataclasses import dataclass
from typing import Self, Type

from pydantic import ConfigDict, Field

from sampletones_shared.application import (
    SAMPLETONES_LIBRARY_DATA_VERSION,
    SAMPLETONES_NAME,
    SAMPLETONES_RECONSTRUCTION_DATA_VERSION,
    SAMPLETONES_VERSION,
)
from sampletones_shared.deployment.version import compare_versions
from sampletones_shared.exceptions import InvalidMetadataError
from sampletones_shared.exceptions.version import IncompatibleVersionError

from .model import DataModel


class Metadata(DataModel):
    model_config = ConfigDict(frozen=True)

    application_name: str = Field(default=SAMPLETONES_NAME)
    version: str = Field(default=SAMPLETONES_VERSION)
    library_data_version: str = Field(default=SAMPLETONES_LIBRARY_DATA_VERSION)
    reconstruction_data_version: str = Field(default=SAMPLETONES_RECONSTRUCTION_DATA_VERSION)

    @classmethod
    def default(cls) -> Self:
        return cls()


@dataclass(frozen=True)
class MetadataContract:
    """The terms a stored file is read under: the data version a build accepts, and what refusing one means.

    A format states its contract once and holds every file it opens against it, so a file written
    by another application or at another data version is refused with an error naming the format
    that refused it.
    """

    label: str
    expected_version: str
    error: Type[IncompatibleVersionError]

    def validate(self, metadata: Metadata, actual_version: str) -> None:
        """Holds what a file states about itself against the build reading it.

        Args:
            metadata: What the file states about its writer.
            actual_version: The data version the file was written at.

        Raises:
            InvalidMetadataError: If the metadata names an application other than SampleToNES.
            IncompatibleVersionError: Of this contract's type, if the file's version departs from
                the one this build accepts.
        """
        if metadata.application_name != SAMPLETONES_NAME:
            raise InvalidMetadataError(
                f"Metadata application name mismatch: expected {SAMPLETONES_NAME}, got {metadata.application_name}."
            )

        if compare_versions(actual_version, self.expected_version) != 0:
            raise self.error(
                f"{self.label} version mismatch: expected {self.expected_version}, got {actual_version}.",
                expected_version=self.expected_version,
                actual_version=actual_version,
            )
