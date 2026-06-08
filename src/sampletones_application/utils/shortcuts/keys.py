from enum import Enum
from typing import Dict, Final

import dearpygui.dearpygui as dpg


class Modifier(Enum):
    CTRL = "Ctrl"
    SHIFT = "Shift"
    ALT = "Alt"


KEY_DISPLAY_NAMES: Dict[int, str] = {
    dpg.mvKey_A: "A",
    dpg.mvKey_B: "B",
    dpg.mvKey_C: "C",
    dpg.mvKey_D: "D",
    dpg.mvKey_E: "E",
    dpg.mvKey_F: "F",
    dpg.mvKey_G: "G",
    dpg.mvKey_H: "H",
    dpg.mvKey_I: "I",
    dpg.mvKey_J: "J",
    dpg.mvKey_K: "K",
    dpg.mvKey_L: "L",
    dpg.mvKey_M: "M",
    dpg.mvKey_N: "N",
    dpg.mvKey_O: "O",
    dpg.mvKey_P: "P",
    dpg.mvKey_Q: "Q",
    dpg.mvKey_R: "R",
    dpg.mvKey_S: "S",
    dpg.mvKey_T: "T",
    dpg.mvKey_U: "U",
    dpg.mvKey_V: "V",
    dpg.mvKey_W: "W",
    dpg.mvKey_X: "X",
    dpg.mvKey_Y: "Y",
    dpg.mvKey_Z: "Z",
    dpg.mvKey_0: "0",
    dpg.mvKey_1: "1",
    dpg.mvKey_2: "2",
    dpg.mvKey_3: "3",
    dpg.mvKey_4: "4",
    dpg.mvKey_5: "5",
    dpg.mvKey_6: "6",
    dpg.mvKey_7: "7",
    dpg.mvKey_8: "8",
    dpg.mvKey_9: "9",
    dpg.mvKey_F1: "F1",
    dpg.mvKey_F2: "F2",
    dpg.mvKey_F3: "F3",
    dpg.mvKey_F4: "F4",
    dpg.mvKey_F5: "F5",
    dpg.mvKey_F6: "F6",
    dpg.mvKey_F7: "F7",
    dpg.mvKey_F8: "F8",
    dpg.mvKey_F9: "F9",
    dpg.mvKey_F10: "F10",
    dpg.mvKey_F11: "F11",
    dpg.mvKey_F12: "F12",
    dpg.mvKey_Escape: "Esc",
    dpg.mvKey_Return: "Enter",
    dpg.mvKey_Tab: "Tab",
    dpg.mvKey_Spacebar: "Space",
    dpg.mvKey_Back: "Backspace",
    dpg.mvKey_Delete: "Del",
    dpg.mvKey_Insert: "Ins",
    dpg.mvKey_Home: "Home",
    dpg.mvKey_End: "End",
    dpg.mvKey_Prior: "PgUp",
    dpg.mvKey_Next: "PgDn",
    dpg.mvKey_Up: "Up",
    dpg.mvKey_Down: "Down",
    dpg.mvKey_Left: "Left",
    dpg.mvKey_Right: "Right",
}


HEX_KEYS: Final[Dict[int, str]] = {dpg.mvKey_0 + i: str(i) for i in range(10)} | {
    dpg.mvKey_A + i: "ABCDEF"[i] for i in range(6)
}
