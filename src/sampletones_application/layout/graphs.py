from pydantic import BaseModel

from sampletones_application.utils.color import RGBA


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
    color_dim: RGBA
    color_bright: RGBA


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
    bar_plot: RGBA
    bar_plot_zero_line: RGBA
    waveform_default: RGBA
    waveform_sample: RGBA
    waveform_reconstruction: RGBA
    waveform_position_indicator: RGBA
    waveform_overlay: RGBA


class GraphsLayout(BaseModel, extra="forbid", frozen=True):
    dimensions: GraphDimensions
    waveform: WaveformLayout
    spectrum: SpectrumLayout
    graph: GraphRange
    bar_plot: BarPlotLayout
    colors: GraphColors
