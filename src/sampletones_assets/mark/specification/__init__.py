from typing import Self

from pydantic import BaseModel, Field

from sampletones_assets.mark.paths import MARK_PATH
from sampletones_assets.mark.specification.colors import MarkColors
from sampletones_assets.mark.specification.frame import MarkFrame
from sampletones_assets.mark.specification.render import MarkRender
from sampletones_assets.mark.specification.waves import MarkWaves
from sampletones_shared.utils.serialization import load_yaml_model


class Mark(BaseModel, extra="forbid", frozen=True):
    """The design definition of the application mark.

    Every shipped icon derives from this one definition — the vector, the raster the
    application loads, and the multi-resolution Windows icon — so the mark is drawn from a
    single source and stays the same shape at every size. Coordinates are written on the
    frame's grid, which keeps the wave edges on whole pixels once the grid is scaled to an
    icon size.
    """

    frame: MarkFrame = Field(description="The rounded square the mark sits on.")
    colors: MarkColors = Field(description="The colours the mark is drawn in.")
    waves: MarkWaves = Field(description="The wave crossing the frame.")
    render: MarkRender = Field(description="How the mark is rasterized.")

    @classmethod
    def load(cls) -> Self:
        """Load the packaged mark definition.

        Returns:
            The mark validated from `sampletones_assets/mark/mark.yaml`.

        Raises:
            TypeError: If the definition file holds anything other than a mapping.
        """
        return load_yaml_model(MARK_PATH, cls)
