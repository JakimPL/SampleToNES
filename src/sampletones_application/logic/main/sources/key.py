from dataclasses import dataclass
from pathlib import Path
from typing import Self

from sampletones_application.constants.sources import SourceKind


@dataclass(frozen=True)
class SourceKey:
    """What a gesture names: one recording, or one folder standing for the recordings below it.

    A path alone leaves the two kinds to be told apart by looking them up, so a key carries the
    kind it was made for and every layer reads the same answer.
    """

    kind: SourceKind
    path: Path

    @classmethod
    def recording(cls, path: Path) -> Self:
        """The key naming the recording at ``path``."""
        return cls(kind=SourceKind.RECORDING, path=path)

    @classmethod
    def folder(cls, root: Path) -> Self:
        """The key naming the folder gathered at ``root``."""
        return cls(kind=SourceKind.FOLDER, path=root)

    @property
    def names_folder(self) -> bool:
        return self.kind is SourceKind.FOLDER
