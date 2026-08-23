from typing import Optional, Self
from uuid import uuid4

from sampletones_core.reconstructions import Reconstruction


class Sample:
    """A reconstruction placed in a project as a playable voice.

    The reconstruction carries one instruction stream per channel; the sample adds what a song
    needs of it — a name, a stable id the tracker rows reference, and the tick its instructions
    repeat from while a note is held.
    """

    def __init__(
        self,
        name: str,
        reconstruction: Reconstruction,
        *,
        loop_point: Optional[int] = None,
    ) -> None:
        self.id: str = uuid4().hex
        self.name: str = name
        self.reconstruction: Reconstruction = reconstruction
        self.loop_point: Optional[int] = loop_point

    @property
    def loops(self) -> bool:
        """Whether the sample repeats its instructions rather than playing them once."""
        return self.loop_point is not None

    def clone(self) -> Self:
        """Return an independent copy with a fresh id.

        The reconstruction is deep-copied so the copy can be edited independently of
        the original; the name and loop point are carried over.
        """
        return type(self)(
            name=self.name,
            reconstruction=self.reconstruction.model_copy(deep=True),
            loop_point=self.loop_point,
        )

    def __hash__(self) -> int:
        return hash(self.id)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Sample) and self.id == other.id

    def __repr__(self) -> str:
        return f"Sample(id={self.id!r}, name={self.name!r})"
