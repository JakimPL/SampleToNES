from pydantic import BaseModel

from sampletones_application.utils.color import RGBA


class BarPlotRange(BaseModel, frozen=True):
    min_y: float
    max_y: float


class BarPlotsLayout(BaseModel, frozen=True):
    arpeggio: BarPlotRange
    pitch: BarPlotRange
    volume: BarPlotRange
    duty_cycle: BarPlotRange


class ReconstructionColors(BaseModel, frozen=True):
    pitch: RGBA
    volume: RGBA
    arpeggio: RGBA
    duty_cycle: RGBA


class ReconstructionsLayout(BaseModel, frozen=True):
    bar_plots: BarPlotsLayout
    colors: ReconstructionColors
