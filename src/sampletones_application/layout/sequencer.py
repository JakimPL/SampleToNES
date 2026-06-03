from pydantic import BaseModel

RGBA = tuple[int, int, int, int]


class SequencerTableCells(BaseModel, frozen=True):
    row: int
    sample: int
    generator: int
    instrument_id: int
    instrument_name: int


class TempoLayout(BaseModel, frozen=True):
    min: int
    max: int
    default: int


class SpeedLayout(BaseModel, frozen=True):
    min: int
    max: int
    default: int


class TrackerLayout(BaseModel, frozen=True):
    rows: int
    row_height: int


class SequencerColors(BaseModel, frozen=True):
    pattern_highlight: RGBA


class SequencerLayout(BaseModel, frozen=True):
    instruments_panel_width: int
    table_cells: SequencerTableCells
    tempo: TempoLayout
    speed: SpeedLayout
    tracker: TrackerLayout
    colors: SequencerColors
