from typing import Dict, Final, Optional, Tuple

import dearpygui.dearpygui as dpg

from sampletones_application.utils.gui.keyboard.event import KeyEvent
from sampletones_shared.constants.music import OCTAVE_SEMITONES

_LOWER_ROW: Final[Tuple[int, ...]] = (
    dpg.mvKey_Z,
    dpg.mvKey_S,
    dpg.mvKey_X,
    dpg.mvKey_D,
    dpg.mvKey_C,
    dpg.mvKey_V,
    dpg.mvKey_G,
    dpg.mvKey_B,
    dpg.mvKey_H,
    dpg.mvKey_N,
    dpg.mvKey_J,
    dpg.mvKey_M,
)

_UPPER_ROW: Final[Tuple[int, ...]] = (
    dpg.mvKey_Q,
    dpg.mvKey_2,
    dpg.mvKey_W,
    dpg.mvKey_3,
    dpg.mvKey_E,
    dpg.mvKey_R,
    dpg.mvKey_5,
    dpg.mvKey_T,
    dpg.mvKey_6,
    dpg.mvKey_Y,
    dpg.mvKey_7,
    dpg.mvKey_U,
)

PIANO_KEYS: Final[Dict[int, int]] = {
    **{key: semitone for semitone, key in enumerate(_LOWER_ROW)},
    **{key: OCTAVE_SEMITONES + semitone for semitone, key in enumerate(_UPPER_ROW)},
}
"""Each note key, as the semitones it stands above the C of the octave being typed at.

Two rows of the keyboard make two octaves of a piano, the way a tracker lays them out: the
bottom row opens at the octave in force and the top row an octave above it, with the black keys
on the row over each.
"""


def semitone_of(event: KeyEvent) -> Optional[int]:
    """The note a plain press of a piano key names, as semitones above the C being typed at.

    A note key held with Ctrl, Alt or Super is a combination, which belongs to the shortcuts, so
    Ctrl+Z undoes wherever the Z key plays a C.

    Args:
        event: The press, carrying the modifiers held as it fired.

    Returns:
        Optional[int]: The semitones the key stands above the C, or ``None`` for a press that
        names no note.
    """
    if not event.is_plain:
        return None

    return PIANO_KEYS.get(event.key)
