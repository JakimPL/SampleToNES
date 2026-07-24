from pydantic import BaseModel


class WaveformLayout(BaseModel, extra="forbid", frozen=True):
    reconstruction_dim_opacity: float
    zoom_factor: float
    max_display_points: int
