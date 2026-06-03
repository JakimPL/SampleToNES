from pydantic import BaseModel

RGBA = tuple[int, int, int, int]
Padding = tuple[int, int]


class InitialPitchTableLayout(BaseModel, frozen=True):
    label_width: int
    display_width: int
    button_width: int
    cell_padding: Padding


class ReconstructionValues(BaseModel, frozen=True):
    pitch_change_delay: float


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
    initial_pitch_table: InitialPitchTableLayout
    values: ReconstructionValues
    bar_plots: BarPlotsLayout
    colors: ReconstructionColors
