from typing import Optional

from sampletones.reconstructions import Reconstruction


class Regenerator:
    def __init__(self) -> None:
        self._current_reconstruction: Optional[Reconstruction] = None

    def regenerate(self) -> Reconstruction:
        if self._current_reconstruction is None:
            raise RuntimeError("No reconstruction available to regenerate.")
