from pydantic import BaseModel

from sampletones_application.layout.primitives import Dimensions
from sampletones_application.layout.tabs.sequencer.colors import SequencerColors
from sampletones_application.layout.tabs.sequencer.history import HistoryLayout
from sampletones_application.layout.tabs.sequencer.order import OrderLayout
from sampletones_application.layout.tabs.sequencer.speed import SpeedLayout
from sampletones_application.layout.tabs.sequencer.table_cells import SequencerTableCells
from sampletones_application.layout.tabs.sequencer.tempo import TempoLayout
from sampletones_application.layout.tabs.sequencer.tracker import TrackerLayout


class SequencerLayout(BaseModel, extra="forbid", frozen=True):
    order: OrderLayout
    table_cells: SequencerTableCells
    tempo: TempoLayout
    speed: SpeedLayout
    tracker: TrackerLayout
    history: HistoryLayout
    colors: SequencerColors
    right_column: Dimensions
