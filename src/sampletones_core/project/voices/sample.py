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
        """Return an independent copy with a fresh id.

        The reconstruction is deep-copied so the copy can be edited independently of
        the original; the name is carried over.
        """
        return type(self)(
            name=self.name,
            reconstruction=self.reconstruction.model_copy(deep=True),
        )

    def __hash__(self) -> int:
        return hash(self.id)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Sample) and self.id == other.id

    def __repr__(self) -> str:
        return f"Sample(id={self.id!r}, name={self.name!r})"
