from pydantic import BaseModel

from sampletones_application.layout.primitives import Padding
from sampletones_application.layout.sequencer.colors import SequencerColors
from sampletones_application.layout.sequencer.history import HistoryLayout
from sampletones_application.layout.sequencer.order import OrderLayout
from sampletones_application.layout.sequencer.speed import SpeedLayout
from sampletones_application.layout.sequencer.table_cells import SequencerTableCells
from sampletones_application.layout.sequencer.tempo import TempoLayout
from sampletones_application.layout.sequencer.tracker import TrackerLayout


class SequencerLayout(BaseModel, extra="forbid", frozen=True):
    cell_padding: Padding
    order: OrderLayout
    table_cells: SequencerTableCells
    tempo: TempoLayout
    speed: SpeedLayout
    tracker: TrackerLayout
    history: HistoryLayout
    colors: SequencerColors
