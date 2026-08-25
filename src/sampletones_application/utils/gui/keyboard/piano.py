from typing import Dict, Final, Tuple

import dearpygui.dearpygui as dpg

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
