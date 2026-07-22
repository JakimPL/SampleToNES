from pydantic import BaseModel

from sampletones_application.layout.primitives import Dimensions


class ReconstructionLayout(BaseModel, extra="forbid", frozen=True):
    right_column: Dimensions
