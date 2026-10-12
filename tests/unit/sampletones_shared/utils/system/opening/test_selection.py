from typing import Optional, Type

import pytest

from sampletones_shared.utils.system.opening.browser import BrowserFileOpener
from sampletones_shared.utils.system.opening.selection import select_file_opener
from sampletones_shared.utils.system.opening.xdg_open import XdgOpenFileOpener
from sampletones_shared.utils.system.system import System

CURRENT_SYSTEM = "sampletones_shared.utils.system.opening.selection.System.current"
WHICH = "sampletones_shared.utils.system.opening.selection.shutil.which"


@pytest.mark.parametrize(
    ("system", "xdg_open", "expected"),
    [
        (System.LINUX, "/usr/bin/xdg-open", XdgOpenFileOpener),
        (System.LINUX, None, BrowserFileOpener),
        (System.MACOS, None, BrowserFileOpener),
        (System.WINDOWS, None, BrowserFileOpener),
    ],
    ids=["linux desktop", "linux without xdg-open", "macos", "windows"],
)
def test_the_opener_fits_the_system(
    monkeypatch: pytest.MonkeyPatch,
    system: System,
    xdg_open: Optional[str],
    expected: Type[object],
) -> None:
    monkeypatch.setattr(CURRENT_SYSTEM, lambda: system)
    monkeypatch.setattr(WHICH, lambda name: xdg_open)

    assert isinstance(select_file_opener(), expected)
