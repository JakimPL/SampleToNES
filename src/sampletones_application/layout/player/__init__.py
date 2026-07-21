from pydantic import BaseModel

from sampletones_application.layout.player.toolbar import PlayerToolbarLayout
from sampletones_application.layout.primitives import Dimensions


class PlayerLayout(BaseModel, extra="forbid", frozen=True):
    toolbar: PlayerToolbarLayout
    button: Dimensions
