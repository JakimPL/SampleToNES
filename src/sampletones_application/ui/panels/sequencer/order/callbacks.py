from typing import Callable, Optional, Tuple

from sampletones_application.ui.panels.sequencer.grid.surface.edit import GridEditSurface
from sampletones_application.ui.panels.sequencer.input.order import OrderCursor
from sampletones_application.ui.panels.sequencer.input.target import OrderTarget
from sampletones_application.view_model.sequencer.region import OrderCell, OrderRegion
from sampletones_core.constants.enums import ChannelName

OrderKey = Tuple[Optional[ChannelName], int]

OnFrameSelectedCallback = Callable[[int], None]
OnRemoveCallback = Callable[[int], None]
OnFrameActionCallback = Callable[[int], None]
OnMoveCallback = Callable[[int, int], None]
OnSetOrderEntryCallback = Callable[[ChannelName, int, Optional[int]], None]
OnSetMasterEntryCallback = Callable[[int, Optional[int]], None]
OnChannelMuteToggledCallback = Callable[[ChannelName], None]
OnChannelSoloedCallback = Callable[[ChannelName], None]
OnBlockRegionCallback = Callable[[OrderRegion], None]
OnPasteBlockCallback = Callable[[OrderCell], None]
CanPasteBlockQuery = Callable[[], bool]

OrderEditSurface = GridEditSurface[OrderCursor, OrderRegion, OrderCell, OrderTarget]
