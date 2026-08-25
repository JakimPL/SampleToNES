from typing import Tuple

from pydantic import BaseModel

from sampletones_application.view_model.reconstruction.paths.state import ReconstructionPathState


class ReconstructionPathViewModel(BaseModel, frozen=True):
    state: ReconstructionPathState
    paths: Tuple[str, ...] = ()

    @property
    def path(self) -> str:
        """The single path the location carries, empty while it holds none or several."""
        if len(self.paths) == 1:
            return self.paths[0]

        return ""
