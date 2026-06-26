from typing import Self
from uuid import uuid4

from sampletones_core.reconstructions import Reconstruction


class Sample:
    def __init__(
        self,
        name: str,
        reconstruction: Reconstruction,
        *,
        loop: bool = False,
    ) -> None:
        self.id: str = uuid4().hex
        self.name: str = name
        self.reconstruction: Reconstruction = reconstruction
        self.loop: bool = loop

    def clone(self) -> Self:
        """Return an independent copy with a fresh id.

        The reconstruction is deep-copied so the copy can be edited without affecting
        the original; the name and loop flag are carried over.
        """
        return type(self)(
            name=self.name,
            reconstruction=self.reconstruction.model_copy(deep=True),
            loop=self.loop,
        )

    def __hash__(self) -> int:
        return hash(self.id)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Sample) and self.id == other.id

    def __repr__(self) -> str:
        return f"Sample(id={self.id!r}, name={self.name!r})"
