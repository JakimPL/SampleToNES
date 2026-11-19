from enum import StrEnum
from pathlib import Path
from typing import List, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, NonNegativeInt, PositiveInt, model_validator

from sampletones_shared.utils.serialization import load_yaml_model


class Split(StrEnum):
    """Which part of a local corpus a sound belongs to.

    A ``review`` sound is listened to while tuning. A ``held-out`` sound is kept out of listening, so
    a change that improves the review sounds is confirmed on sounds it was never tuned on.
    """

    REVIEW = "review"
    HELD_OUT = "held-out"


class NesmdbPiece(BaseModel):
    """A window of a piece from an NES-MDB archive of MIDI files.

    Attributes:
        kind: Marks the item as an NES-MDB piece.
        name: The name its files are written under.
        archive: The archive holding the piece, relative to the manifest's own folder.
        member: The piece's file inside the archive.
        start_frame: The first frame of the window.
        frames: How many frames the window holds.
        split: Which part of the corpus the piece belongs to.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: Literal["nesmdb"]
    name: str
    archive: Path
    member: str
    start_frame: NonNegativeInt
    frames: PositiveInt
    split: Split


class CorpusManifest(BaseModel):
    """Reference sounds kept outside the package, on the machine the run measures on.

    Attributes:
        items: The sounds, in the order the corpus holds them.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    items: List[NesmdbPiece] = Field(min_length=1)

    @model_validator(mode="after")
    def _validate_unique_names(self) -> Self:
        names = [item.name for item in self.items]
        if len(set(names)) != len(names):
            raise ValueError("Every sound of a manifest must have a name of its own")

        return self

    @classmethod
    def read(cls, path: Path) -> Self:
        """The manifest at ``path``, every archive it names resolved against the manifest's folder.

        Raises:
            ValidationError: If the file holds no manifest.
        """
        manifest = load_yaml_model(path, cls)
        folder = path.parent
        return manifest.model_copy(
            update={"items": [item.model_copy(update={"archive": folder / item.archive}) for item in manifest.items]}
        )
