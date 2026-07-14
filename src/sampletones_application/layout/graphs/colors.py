from pydantic import BaseModel

from sampletones_application.utils.palette import PaletteColor


class GraphColors(BaseModel, extra="forbid", frozen=True):
    bar_plot: PaletteColor
    bar_plot_zero_line: PaletteColor
    waveform_default: PaletteColor
    waveform_sample: PaletteColor
    waveform_reconstruction: PaletteColor
    waveform_position_indicator: PaletteColor
    waveform_overlay: PaletteColor
