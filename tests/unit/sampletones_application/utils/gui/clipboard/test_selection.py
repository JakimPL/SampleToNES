from dataclasses import dataclass
from typing import Final, Optional, Type
from unittest.mock import MagicMock, patch

import pytest

from sampletones_application.utils.gui.clipboard.backends.dearpygui import DearPyGuiTextClipboard
from sampletones_application.utils.gui.clipboard.backends.x11.clipboard import X11TextClipboard
from sampletones_application.utils.gui.clipboard.protocol import TextClipboard
from sampletones_application.utils.gui.clipboard.selection import (
    DISPLAY_VARIABLE,
    select_text_clipboard,
)
from sampletones_shared.utils.system.system import System
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase

MODULE: Final[str] = "sampletones_application.utils.gui.clipboard.selection"
DISPLAY: Final[str] = ":7"


class TestTheClipboardFitsTheEnvironment(BaseTestSuite):
    """Linux reads over a connection of its own while it can reach the display; elsewhere DearPyGui serves."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        system: System
        display: Optional[str]
        xcb_loads: bool
        expected: Type[TextClipboard]

    test_cases = (
        TestCase(
            label="linux_on_a_display",
            system=System.LINUX,
            display=DISPLAY,
            xcb_loads=True,
            expected=X11TextClipboard,
        ),
        TestCase(
            label="linux_naming_no_display",
            system=System.LINUX,
            display=None,
            xcb_loads=True,
            expected=DearPyGuiTextClipboard,
        ),
        TestCase(
            label="linux_lacking_libxcb",
            system=System.LINUX,
            display=DISPLAY,
            xcb_loads=False,
            expected=DearPyGuiTextClipboard,
        ),
        TestCase(
            label="windows",
            system=System.WINDOWS,
            display=None,
            xcb_loads=False,
            expected=DearPyGuiTextClipboard,
        ),
        TestCase(
            label="macos",
            system=System.MACOS,
            display=DISPLAY,
            xcb_loads=False,
            expected=DearPyGuiTextClipboard,
        ),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_selected_clipboard_fits(self, test_case: TestCase, monkeypatch: pytest.MonkeyPatch) -> None:
        if test_case.display is None:
            monkeypatch.delenv(DISPLAY_VARIABLE, raising=False)
        else:
            monkeypatch.setenv(DISPLAY_VARIABLE, test_case.display)

        with (
            patch(f"{MODULE}.System.current", return_value=test_case.system),
            patch(f"{MODULE}.load_xcb", return_value=MagicMock() if test_case.xcb_loads else None),
        ):
            clipboard = select_text_clipboard()

        assert isinstance(clipboard, test_case.expected)
