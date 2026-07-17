from pydantic import BaseModel

from sampletones_application.layout.graphs.bar_plot import BarPlotLayout
from sampletones_application.layout.graphs.colors import GraphColors
from sampletones_application.layout.graphs.dimensions import GraphDimensions
from sampletones_application.layout.graphs.graph import GraphRange
from sampletones_application.layout.graphs.spectrum import SpectrumLayout
from sampletones_application.layout.graphs.waveform import WaveformLayout


class GraphsLayout(BaseModel, extra="forbid", frozen=True):
    dimensions: GraphDimensions
    waveform: WaveformLayout
    spectrum: SpectrumLayout
    graph: GraphRange
    bar_plot: BarPlotLayout
    colors: GraphColors
