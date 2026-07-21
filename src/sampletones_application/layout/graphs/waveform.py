from pydantic import BaseModel


class WaveformLayout(BaseModel, extra="forbid", frozen=True):
    sample_thickness: float
    reconstruction_thickness: float
    position_indicator_thickness: float
    reconstruction_dim_opacity: float
    zoom_factor: float
    max_display_points: int
