from pydantic import BaseModel

from sampletones_application.layout.general import Padding
from sampletones_application.utils.color import RGBA


class OrderLayout(BaseModel, frozen=True):
    height: int
    position_column_width: int


class SequencerTableCells(BaseModel, frozen=True):
    row: int
    sample: int
    divider: int
    generator: int
    instrument_id: int
    instrument_name: int
    instrument_loop: int


class TempoLayout(BaseModel, frozen=True):
    min: int
    max: int
    default: int


class SpeedLayout(BaseModel, frozen=True):
    min: int
    max: int
    default: int


class SubcolumnWidths(BaseModel, frozen=True):
    instrument: int
    transpose: int
    volume: int


class SubcolumnColors(BaseModel, frozen=True):
    instrument: RGBA
    transpose: RGBA
    volume: RGBA


class TrackerLayout(BaseModel, frozen=True):
    rows: int
    row_height: int
    page_size: int
    subcolumn_widths: SubcolumnWidths


class SequencerColors(BaseModel, frozen=True):
    pattern_highlight: RGBA
    cell_cursor: RGBA
    cursor_row: RGBA
    sample_column: RGBA
    sample_divider: RGBA
    order_label: RGBA
    order_column: RGBA
    order_column_alternate: RGBA
    order_column_current: RGBA
    subcolumns: SubcolumnColors


class SequencerLayout(BaseModel, frozen=True):
    samples_panel_width: int
    cell_padding: Padding
    order: OrderLayout
    table_cells: SequencerTableCells
    tempo: TempoLayout
    speed: SpeedLayout
    tracker: TrackerLayout
    colors: SequencerColors
