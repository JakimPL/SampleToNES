from typing import Callable, Dict, Final, Tuple

from sampletones_application.categories.elements.sequencer import SequencerTrackerElements
from sampletones_application.utils.gui.shortcuts.ids import ShortcutId
from sampletones_application.view_model.sequencer.region import TrackerRegion
from sampletones_core.constants.general import MAX_VOLUME
from sampletones_shared.constants.music import OCTAVE_SEMITONES, SEMITONE_STEP
from sampletones_shared.types.application import Sender

VOLUME_FINE_STEP: Final[int] = 1
VOLUME_COARSE_STEP: Final[int] = (MAX_VOLUME + 1) // 4

AdjustAction = Tuple[SequencerTrackerElements, ShortcutId, int]
AdjustMenuCallback = Callable[[Sender, None, Tuple[TrackerRegion, int]], None]

TRANSPOSE_ACTIONS: Final[Tuple[AdjustAction, ...]] = (
    (
        SequencerTrackerElements.CONTEXT_TRANSPOSE_UP,
        ShortcutId.TRACKER_TRANSPOSE_UP,
        SEMITONE_STEP,
    ),
    (
        SequencerTrackerElements.CONTEXT_TRANSPOSE_DOWN,
        ShortcutId.TRACKER_TRANSPOSE_DOWN,
        -SEMITONE_STEP,
    ),
    (
        SequencerTrackerElements.CONTEXT_TRANSPOSE_OCTAVE_UP,
        ShortcutId.TRACKER_TRANSPOSE_OCTAVE_UP,
        OCTAVE_SEMITONES,
    ),
    (
        SequencerTrackerElements.CONTEXT_TRANSPOSE_OCTAVE_DOWN,
        ShortcutId.TRACKER_TRANSPOSE_OCTAVE_DOWN,
        -OCTAVE_SEMITONES,
    ),
)

VOLUME_ACTIONS: Final[Tuple[AdjustAction, ...]] = (
    (
        SequencerTrackerElements.CONTEXT_VOLUME_UP,
        ShortcutId.TRACKER_VOLUME_UP,
        VOLUME_FINE_STEP,
    ),
    (
        SequencerTrackerElements.CONTEXT_VOLUME_DOWN,
        ShortcutId.TRACKER_VOLUME_DOWN,
        -VOLUME_FINE_STEP,
    ),
    (
        SequencerTrackerElements.CONTEXT_VOLUME_UP_COARSE,
        ShortcutId.TRACKER_VOLUME_UP_COARSE,
        VOLUME_COARSE_STEP,
    ),
    (
        SequencerTrackerElements.CONTEXT_VOLUME_DOWN_COARSE,
        ShortcutId.TRACKER_VOLUME_DOWN_COARSE,
        -VOLUME_COARSE_STEP,
    ),
)


def _steps(actions: Tuple[AdjustAction, ...]) -> Dict[ShortcutId, int]:
    return {shortcut_id: delta for _, shortcut_id, delta in actions}


TRANSPOSE_STEPS: Final[Dict[ShortcutId, int]] = _steps(TRANSPOSE_ACTIONS)
VOLUME_STEPS: Final[Dict[ShortcutId, int]] = _steps(VOLUME_ACTIONS)
