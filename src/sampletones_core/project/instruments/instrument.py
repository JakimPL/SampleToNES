from uuid import uuid4

from sampletones_core.reconstructions import Reconstruction


class Instrument:
    def __init__(self, name: str, reconstruction: Reconstruction) -> None:
        self.id: str = uuid4().hex
        self.name: str = name
        self.reconstruction: Reconstruction = reconstruction

    def __hash__(self) -> int:
        return hash(self.id)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Instrument) and self.id == other.id

    def __repr__(self) -> str:
        return f"Instrument(id={self.id!r}, name={self.name!r})"
