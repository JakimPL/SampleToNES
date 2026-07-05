from pydantic import BaseModel


class BarPlotRange(BaseModel, frozen=True):
    min_y: float
    max_y: float


class BarPlotsLayout(BaseModel, frozen=True):
    arpeggio: BarPlotRange
    pitch: BarPlotRange
    volume: BarPlotRange
    duty_cycle: BarPlotRange


class ReconstructionsLayout(BaseModel, frozen=True):
    bar_plots: BarPlotsLayout
