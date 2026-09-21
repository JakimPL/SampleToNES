from pathlib import Path
from typing import Optional, Self

from pydantic import ConfigDict, Field, field_serializer

from sampletones_core.data import DataModel


class StemSource(DataModel):
    """Where one recording came from, and what it was called.

    A recording's name belongs to the document that was built from it, while the file it lives
    in belongs to the machine the conversion ran on. Keeping the two apart is what lets a
    reconstruction embedded in a project still name the recordings behind its frames.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    stem_id: int = Field(
        ...,
        description="The stems entry this recording was converted as",
    )
    name: str = Field(
        ...,
        description="What the recording is called",
    )
    path: Optional[Path] = Field(
        default=None,
        description="Where the recording lives on this machine, absent once detached from its origin",
    )

    @classmethod
    def of(cls, stem_id: int, path: Path) -> Self:
        """The source a conversion records for a recording, named after the file it read."""
        return cls(stem_id=stem_id, name=path.stem, path=path)

    def detached(self) -> Self:
        """The same recording with its location let go of, keeping the name it is known by."""
        return self.__class__(stem_id=self.stem_id, name=self.name, path=None)

    @field_serializer("path")
    def _serialize_path(self, path: Optional[Path]) -> Optional[str]:
        return str(path) if path is not None else None
