from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path
from typing import Any, Final, FrozenSet, Optional, Self

from sampletones_core.configs import InstructionsLibraryConfig
from sampletones_core.data import Metadata
from sampletones_core.data.stored import read_leading_fields
from sampletones_shared.exceptions import (
    IncompatibleLibraryDataVersionError,
    InvalidMetadataError,
)

from .data import LIBRARY_DATA_CONTRACT

METADATA_FIELD: Final[str] = "metadata"
CONFIG_FIELD: Final[str] = "config"
HEADER_FIELDS: Final[FrozenSet[str]] = frozenset({METADATA_FIELD, CONFIG_FIELD})
VERSION_FIELD: Final[str] = "library_data_version"


class LibraryState(Enum):
    """Where a library file stands for the build about to use it.

    A current library is one this build loads. An outdated one is on disk but was written for
    another build, so it is rebuilt before use. A missing one is generated.
    """

    MISSING = auto()
    OUTDATED = auto()
    CURRENT = auto()


@dataclass(frozen=True)
class LibraryHeader:
    """What a library file states about itself at its front: the build that wrote it, and the
    settings it was built for.

    A library stores both ahead of its entries, so they read from the first bytes of the file
    whatever its size. Each is ``None`` where the file states it in no form this build reads.
    """

    metadata: Optional[Metadata]
    config: Optional[InstructionsLibraryConfig]

    @classmethod
    def read(cls, path: Path) -> Self:
        """The header of the library stored at ``path``.

        Raises:
            OSError: If the file cannot be read, a missing one included.
        """
        fields = read_leading_fields(path, HEADER_FIELDS)
        return cls(
            metadata=cls._stored_metadata(fields.get(METADATA_FIELD)),
            config=cls._stored_config(fields.get(CONFIG_FIELD)),
        )

    @property
    def is_current(self) -> bool:
        """Whether this build loads the library, held to the contract a library's load applies."""
        if self.metadata is None:
            return False

        try:
            LIBRARY_DATA_CONTRACT.validate(self.metadata, self.metadata.library_data_version)
        except (InvalidMetadataError, IncompatibleLibraryDataVersionError, ValueError):
            return False

        return True

    @staticmethod
    def _stored_metadata(stored: Any) -> Optional[Metadata]:
        """The metadata a file states, taken from a file naming the library data version it was
        written at.

        Metadata fills a field a file leaves out with the reading build's own version, so a file is
        held to the version it states itself.
        """
        if not isinstance(stored, dict) or not isinstance(stored.get(VERSION_FIELD), str):
            return None

        try:
            return Metadata.deserialize_inner(stored, fast=False)
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _stored_config(stored: Any) -> Optional[InstructionsLibraryConfig]:
        """The settings a file states it was built for, where this build reads them."""
        if not isinstance(stored, dict):
            return None

        try:
            return InstructionsLibraryConfig.deserialize_inner(stored, fast=False)
        except (ValueError, TypeError):
            return None


def library_state(path: Path) -> LibraryState:
    """Where the library stored at ``path`` stands for this build.

    Args:
        path: Where the library file is expected.

    Returns:
        LibraryState: ``CURRENT`` for a file this build loads, ``OUTDATED`` for any other file,
            and ``MISSING`` where there is no file.
    """
    try:
        header = LibraryHeader.read(path)
    except FileNotFoundError:
        return LibraryState.MISSING

    return LibraryState.CURRENT if header.is_current else LibraryState.OUTDATED
