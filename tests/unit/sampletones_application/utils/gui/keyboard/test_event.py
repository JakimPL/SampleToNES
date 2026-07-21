from dataclasses import dataclass
from typing import List
from unittest.mock import MagicMock, patch

import pytest

from sampletones_application.utils.gui.keyboard.event import KeyEvent

MODULE = "sampletones_application.utils.gui.keyboard.event"

KEY = 65
L_CONTROL = 1
R_CONTROL = 2
L_SHIFT = 3
R_SHIFT = 4
L_ALT = 5
R_ALT = 6


def _dpg(held: List[int]) -> MagicMock:
    dpg = MagicMock()
    dpg.mvKey_LControl = L_CONTROL
    dpg.mvKey_RControl = R_CONTROL
    dpg.mvKey_LShift = L_SHIFT
    dpg.mvKey_RShift = R_SHIFT
    dpg.mvKey_LAlt = L_ALT
    dpg.mvKey_RAlt = R_ALT
    dpg.is_key_down.side_effect = lambda key: key in held
    return dpg


@dataclass(frozen=True)
class CaptureCase:
    name: str
    held: List[int]
    ctrl: bool
    shift: bool
    alt: bool


CAPTURE_CASES = [
    CaptureCase("bare key", held=[], ctrl=False, shift=False, alt=False),
    CaptureCase("left control", held=[L_CONTROL], ctrl=True, shift=False, alt=False),
    CaptureCase("right control", held=[R_CONTROL], ctrl=True, shift=False, alt=False),
    CaptureCase("left shift", held=[L_SHIFT], ctrl=False, shift=True, alt=False),
    CaptureCase("right shift", held=[R_SHIFT], ctrl=False, shift=True, alt=False),
    CaptureCase("left alt", held=[L_ALT], ctrl=False, shift=False, alt=True),
    CaptureCase("right alt", held=[R_ALT], ctrl=False, shift=False, alt=True),
    CaptureCase("control and shift", held=[L_CONTROL, R_SHIFT], ctrl=True, shift=True, alt=False),
    CaptureCase("every modifier", held=[L_CONTROL, L_SHIFT, L_ALT], ctrl=True, shift=True, alt=True),
]


@pytest.mark.parametrize("case", CAPTURE_CASES, ids=lambda case: case.name)
def test_capture_snapshots_the_held_modifiers(case: CaptureCase) -> None:
    with patch(f"{MODULE}.dpg", _dpg(case.held)):
        event = KeyEvent.capture(KEY)

    assert event == KeyEvent(key=KEY, ctrl=case.ctrl, shift=case.shift, alt=case.alt)
