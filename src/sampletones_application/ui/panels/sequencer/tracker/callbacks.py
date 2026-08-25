from typing import Callable, Optional, Tuple

from sampletones_application.ui.panels.sequencer.grid.surface.edit import GridEditSurface
from sampletones_application.ui.panels.sequencer.input.target import TrackerTarget
from sampletones_application.ui.panels.sequencer.input.tracker import TrackerCursor
from sampletones_application.view_model.sequencer.region import TrackerCell, TrackerRegion
from sampletones_application.view_model.sequencer.subcolumn import SubColumn
from sampletones_application.view_model.sequencer.voices import VoiceKind
from sampletones_core.constants.enums import ChannelName
from sampletones_shared.types.callback import VoidCallback

OnClearRowCallback = Callable[[int, Optional[ChannelName]], None]
OnClearSubcolumnCallback = Callable[[int, Optional[ChannelName], SubColumn], None]
OnSetRowCallback = Callable[[int, Optional[ChannelName], Optional[str], Optional[int], Optional[int]], None]
OnSetNoteOffCallback = Callable[[int, Optional[ChannelName]], None]
OnNoteTypedCallback = Callable[[int, ChannelName, int], None]
OnCellSelectedCallback = VoidCallback
OnPlayFromRowCallback = Callable[[int], None]
OnPlayFromFrameCallback = VoidCallback
OnAdjustCallback = Callable[[TrackerRegion, int], None]
OnChannelMuteToggledCallback = Callable[[ChannelName], None]
OnChannelSoloedCallback = Callable[[ChannelName], None]
OnBlockRegionCallback = Callable[[TrackerRegion], None]
OnPasteBlockCallback = Callable[[TrackerCell], None]
CanPasteBlockQuery = Callable[[], bool]

TrackerEditSurface = GridEditSurface[TrackerCursor, TrackerRegion, TrackerCell, TrackerTarget]
ThemeKey = Tuple[SubColumn, Optional[VoiceKind]]
