from typing import Self
from uuid import uuid4

from sampletones_core.reconstructions import Reconstruction


class Sample:
    """A reconstruction placed in a project as a playable voice.

    The reconstruction carries one instruction stream per channel; the sample adds what a song
    needs of it — a name and a stable id the tracker rows reference. Its frames are the run its
    conversion found, so a note sounds them through and the channel then rests.
    """

    def __init__(
        self,
        name: str,
        reconstruction: Reconstruction,
    ) -> None:
        self.id: str = uuid4().hex
        self.name: str = name
        self.reconstruction: Reconstruction = reconstruction

    def clone(self) -> Self:
        """Return a copy with a fresh id, holding the same reconstruction and carrying the name.

        A reconstruction never changes once made, and an edit installs a new one in the sample it
        reaches, so the copy and the original share the document until one of them is edited.
        """
        return type(self)(
            name=self.name,
            reconstruction=self.reconstruction,
        )

    def snapshot(self) -> Self:
        """A sample of its own with the same id and name, holding the very same reconstruction."""
        copied = type(self)(name=self.name, reconstruction=self.reconstruction)
        copied.id = self.id
        return copied

    def __hash__(self) -> int:
        return hash(self.id)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Sample) and self.id == other.id

    def __repr__(self) -> str:
        return f"Sample(id={self.id!r}, name={self.name!r})"
