from dataclasses import dataclass
from typing import Dict, Final, Tuple

from sampletones_application.categories.elements.sequencer import (
    SequencerVoicesElements,
)
from sampletones_application.utils.gui.shortcuts.ids import ShortcutId
from sampletones_application.view_model.sequencer.move import MoveDirection


@dataclass(frozen=True)
class VoiceMove:
    """One of the four moves, as its key press and its menu item each name it."""

    element: SequencerVoicesElements
    shortcut: ShortcutId
    direction: MoveDirection


VOICE_MOVES: Final[Tuple[VoiceMove, ...]] = (
    VoiceMove(
        element=SequencerVoicesElements.CONTEXT_MOVE_UP,
        shortcut=ShortcutId.VOICES_MOVE_VOICE_UP,
        direction=MoveDirection.PREVIOUS,
    ),
    VoiceMove(
        element=SequencerVoicesElements.CONTEXT_MOVE_DOWN,
        shortcut=ShortcutId.VOICES_MOVE_VOICE_DOWN,
        direction=MoveDirection.NEXT,
    ),
    VoiceMove(
        element=SequencerVoicesElements.CONTEXT_MOVE_TOP,
        shortcut=ShortcutId.VOICES_MOVE_VOICE_TO_TOP,
        direction=MoveDirection.FIRST,
    ),
    VoiceMove(
        element=SequencerVoicesElements.CONTEXT_MOVE_BOTTOM,
        shortcut=ShortcutId.VOICES_MOVE_VOICE_TO_BOTTOM,
        direction=MoveDirection.LAST,
    ),
)

MOVE_DIRECTIONS: Final[Dict[ShortcutId, MoveDirection]] = {move.shortcut: move.direction for move in VOICE_MOVES}
