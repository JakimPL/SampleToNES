from enum import StrEnum
from pathlib import Path
from typing import Annotated, List, Literal, Optional, Self, Union

from pydantic import BaseModel, ConfigDict, Field, NonNegativeInt, PositiveInt, model_validator

from sampletones_shared.utils.serialization import load_yaml_model

from .names import require_unique_names


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


class RecordingItem(BaseModel):
    """Recordings of real sound: one, or several as stems under a setup.

    Attributes:
        kind: Marks the item as recordings.
        name: The name its files are written under.
        family: The family it joins: ``composites`` for stems, ``samples`` for a recording heard
            for a general sense of quality.
        category: The category it is reported under.
        listed: Whether the page lists it.
        sources: The recordings, relative to the manifest's own folder, one per entry of the setup.
        stems: The stems setup the recordings are converted under, relative to the manifest's
            folder, or ``None`` for one recording converted over the run's channels.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: Literal["recording"]
    name: str
    family: Literal["composites", "samples"]
    category: str
    listed: bool
    sources: List[Path] = Field(min_length=1)
    stems: Optional[Path]

    @model_validator(mode="after")
    def _validate_one_recording_without_stems(self) -> Self:
        if self.stems is None and len(self.sources) != 1:
            raise ValueError(f"{self.name!r} names several recordings and no stems setup to convert them under")

        return self


ManifestItem = Annotated[Union[NesmdbPiece, RecordingItem], Field(discriminator="kind")]


class CorpusManifest(BaseModel):
    """Reference sounds kept outside the package, on the machine the run measures on.

    Attributes:
        items: The sounds, in the order the corpus holds them.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    items: List[ManifestItem] = Field(min_length=1)

    @model_validator(mode="after")
    def _validate_unique_names(self) -> Self:
        require_unique_names([item.name for item in self.items], "sound of a manifest")
        return self

    @classmethod
    def read(cls, path: Path) -> Self:
        """The manifest at ``path``, every archive it names resolved against the manifest's folder.

        Raises:
            ValidationError: If the file holds no manifest.
        """
        manifest = load_yaml_model(path, cls)
        return manifest.model_copy(update={"items": [_resolved(item, path.parent) for item in manifest.items]})

    @property
    def pieces(self) -> List[NesmdbPiece]:
        """The NES-MDB pieces the manifest names."""
        return [item for item in self.items if isinstance(item, NesmdbPiece)]

    @property
    def recordings(self) -> List[RecordingItem]:
        """The recordings the manifest names."""
        return [item for item in self.items if isinstance(item, RecordingItem)]


def _resolved(item: Union[NesmdbPiece, RecordingItem], folder: Path) -> Union[NesmdbPiece, RecordingItem]:
    """The item with every path it names read from ``folder``."""
    match item:
        case NesmdbPiece():
            return item.model_copy(update={"archive": folder / item.archive})
        case RecordingItem():
            stems = folder / item.stems if item.stems is not None else None
            return item.model_copy(update={"sources": [folder / source for source in item.sources], "stems": stems})
