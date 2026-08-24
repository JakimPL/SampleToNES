from typing import Dict, Final

from sampletones_application.utils.gui.shortcuts.ids import ShortcutId
from sampletones_application.view_model.sequencer.move import MoveDirection

MOVE_DIRECTIONS: Final[Dict[ShortcutId, MoveDirection]] = {
    ShortcutId.ORDER_MOVE_FRAME_LEFT: MoveDirection.PREVIOUS,
    ShortcutId.ORDER_MOVE_FRAME_RIGHT: MoveDirection.NEXT,
    ShortcutId.ORDER_MOVE_FRAME_TO_START: MoveDirection.FIRST,
    ShortcutId.ORDER_MOVE_FRAME_TO_END: MoveDirection.LAST,
}
