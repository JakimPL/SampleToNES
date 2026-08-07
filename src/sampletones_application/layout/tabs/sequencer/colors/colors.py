from pydantic import BaseModel

from sampletones_application.layout.tabs.sequencer.colors.channel import ChannelColors
from sampletones_application.layout.tabs.sequencer.colors.header import HeaderColors
from sampletones_application.layout.tabs.sequencer.colors.history import HistoryColors
from sampletones_application.layout.tabs.sequencer.colors.muted import MutedColors
from sampletones_application.layout.tabs.sequencer.colors.order import OrderColors
from sampletones_application.layout.tabs.sequencer.colors.sample import SampleColors
from sampletones_application.layout.tabs.sequencer.colors.tracker import TrackerColors
from sampletones_application.utils.palette.colors.written import WrittenColor


class SequencerColors(BaseModel, extra="forbid", frozen=True):
    pattern_highlight: WrittenColor
    cell_cursor: WrittenColor
    cursor_row: WrittenColor
    playback_row: WrittenColor
    label: WrittenColor
    order: OrderColors
    sample: SampleColors
    header: HeaderColors
    muted: MutedColors
    history: HistoryColors
    text: TrackerColors
    channels: ChannelColors
