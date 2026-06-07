from pydantic import BaseModel

from sampletones_application.utils.color import RGBA


class OrderLayout(BaseModel, frozen=True):
    height: int
    position_column_width: int


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
    cell_cursor: RGBA
    cursor_row: RGBA


class SequencerLayout(BaseModel, frozen=True):
    samples_panel_width: int
    order: OrderLayout
    table_cells: SequencerTableCells
    tempo: TempoLayout
    speed: SpeedLayout
    tracker: TrackerLayout
    colors: SequencerColors
