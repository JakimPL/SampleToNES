from pydantic import BaseModel

from sampletones_application.utils.palette import PaletteColor


class GraphColors(BaseModel, extra="forbid", frozen=True):
    bar_plot: PaletteColor
    waveform_sample: PaletteColor
    waveform_reconstruction: PaletteColor
