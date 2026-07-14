from pydantic import BaseModel

from sampletones_application.utils.palette import PaletteColor


class GraphDimensions(BaseModel, extra="forbid", frozen=True):
    width: int
    height: int
    bar_plot_height: int


class WaveformLayout(BaseModel, extra="forbid", frozen=True):
    sample_thickness: float
    reconstruction_thickness: float
    position_indicator_thickness: float
    zoom_factor: float
    max_display_points: int


class SpectrumLayout(BaseModel, extra="forbid", frozen=True):
    max_display_bins: int
    offset_log: float
    color_dim: PaletteColor
    color_bright: PaletteColor


class GraphRange(BaseModel, extra="forbid", frozen=True):
    min_x: float
    max_x: float
    min_y: float
    max_y: float


class BarPlotLayout(BaseModel, extra="forbid", frozen=True):
    min_x: float
    min_y: float
    max_y: float
    bar_weight: float
    zero_line_thickness: float
    hover_alpha: int


class GraphColors(BaseModel, extra="forbid", frozen=True):
    bar_plot: PaletteColor
    bar_plot_zero_line: PaletteColor
    waveform_default: PaletteColor
    waveform_sample: PaletteColor
    waveform_reconstruction: PaletteColor
    waveform_position_indicator: PaletteColor
    waveform_overlay: PaletteColor


class GraphsLayout(BaseModel, extra="forbid", frozen=True):
    dimensions: GraphDimensions
    waveform: WaveformLayout
    spectrum: SpectrumLayout
    graph: GraphRange
    bar_plot: BarPlotLayout
    colors: GraphColors
