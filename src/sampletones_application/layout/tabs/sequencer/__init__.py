from pydantic import BaseModel

from sampletones_application.layout.primitives import Dimensions
from sampletones_application.layout.tabs.sequencer.colors.colors import SequencerColors
from sampletones_application.layout.tabs.sequencer.history import HistoryLayout
from sampletones_application.layout.tabs.sequencer.order import OrderLayout
from sampletones_application.layout.tabs.sequencer.tables.cells import SequencerTableCells
from sampletones_application.layout.tabs.sequencer.tracker.tracker import TrackerLayout


class SequencerLayout(BaseModel, extra="forbid", frozen=True):
    order: OrderLayout
    table_cells: SequencerTableCells
    tracker: TrackerLayout
    history: HistoryLayout
    colors: SequencerColors
    right_column: Dimensions
