import os
from typing import Final, List, Optional, Type

import pytest

from sampletones_application.utils.file_dialogs.backends.portal import parent as parent_module
from sampletones_application.utils.file_dialogs.backends.portal.parent import (
    NO_PARENT_WINDOW,
    parent_window_handle,
)

WINDOW_ID: Final[int] = 0x2200132
HANDLE: Final[str] = "x11:2200132"


class FakeDisplay:
    """An X server answering with one prepared window, recording the lookups and its release."""

    def __init__(self, window_id: Optional[int]) -> None:
        self._window_id = window_id
        self.processes: List[int] = []
        self.closed = False

    def window_of_process(self, process_id: int) -> Optional[int]:
        self.processes.append(process_id)
        return self._window_id

    def close(self) -> None:
        self.closed = True


def _opening(display: Optional[FakeDisplay]) -> Type[object]:
    class FakeX11Display:
        @staticmethod
        def open() -> Optional[FakeDisplay]:
            return display

    return FakeX11Display


class TestParentWindowHandle:
    def test_the_handle_names_the_window_in_hexadecimal(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(parent_module, "X11Display", _opening(FakeDisplay(WINDOW_ID)))

        assert parent_window_handle() == HANDLE

    def test_the_window_looked_for_is_the_one_this_process_draws_in(self, monkeypatch: pytest.MonkeyPatch) -> None:
        display = FakeDisplay(WINDOW_ID)
        monkeypatch.setattr(parent_module, "X11Display", _opening(display))

        parent_window_handle()

        assert display.processes == [os.getpid()]

    def test_the_connection_is_released_once_the_window_is_found(self, monkeypatch: pytest.MonkeyPatch) -> None:
        display = FakeDisplay(WINDOW_ID)
        monkeypatch.setattr(parent_module, "X11Display", _opening(display))

        parent_window_handle()

        assert display.closed

    def test_a_desktop_listing_no_window_for_this_process_leaves_the_dialog_on_its_own(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        display = FakeDisplay(None)
        monkeypatch.setattr(parent_module, "X11Display", _opening(display))

        assert parent_window_handle() == NO_PARENT_WINDOW
        assert display.closed

    def test_a_session_running_without_x11_leaves_the_dialog_on_its_own(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """A display that stays closed is how a session with no X server answers."""
        monkeypatch.setattr(parent_module, "X11Display", _opening(None))

        assert parent_window_handle() == NO_PARENT_WINDOW
