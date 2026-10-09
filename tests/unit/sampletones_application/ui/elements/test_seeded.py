from typing import Final, Iterator, List
from unittest.mock import MagicMock, patch

import dearpygui.dearpygui as dpg
import pytest

from sampletones_application.layout.primitives import DialogGeometry
from sampletones_application.ui.elements.seeded import GUISeededDialogWindow
from sampletones_application.utils.gui.keyboard import KeyRouter
from sampletones_application.utils.gui.modal_queue import ModalQueue
from sampletones_application.utils.gui.shortcuts.source import ShortcutSource
from tests.suite.frames import Frames, held_frames

__all__ = ["held_frames"]

MODULE: Final[str] = "sampletones_application.ui.elements.window"
TAG: Final[str] = "test.dialog.window.seeded"
STANDING_TAG: Final[str] = "test.dialog.window.standing"
FIRST_SEED: Final[str] = "first"
NEWER_SEED: Final[str] = "newer"
PROBE_WIDTH: Final[int] = 200
PROBE_HEIGHT: Final[int] = 100
VIEWPORT_WIDTH: Final[int] = 800
VIEWPORT_HEIGHT: Final[int] = 600


class ProbeSeededWindow(GUISeededDialogWindow[str]):
    """A dialog drawing one word, which records every word it drew."""

    def __init__(self, router: KeyRouter) -> None:
        self.drawn: List[str] = []
        super().__init__(
            TAG,
            DialogGeometry(width=PROBE_WIDTH, height=PROBE_HEIGHT),
            subject="probe",
            key_router=router,
            shortcut_source=MagicMock(spec=ShortcutSource),
        )

    def create_window(self) -> None:
        with self.dialog_window(label="probe", on_close=None):
            dpg.add_text(self.view_model)

        self.drawn.append(self.view_model)

    def _render(self) -> None:
        self.drawn.append(self.view_model)


@pytest.fixture(name="dpg_context")
def dpg_context_fixture() -> Iterator[None]:
    dpg.create_context()
    with (
        patch(f"{MODULE}.ThemeRegistry"),
        patch(f"{MODULE}.center_when_settled"),
        patch.object(dpg, "get_viewport_client_width", return_value=VIEWPORT_WIDTH),
        patch.object(dpg, "get_viewport_client_height", return_value=VIEWPORT_HEIGHT),
    ):
        try:
            yield
        finally:
            dpg.destroy_context()


class TestASeededWindowWaitingForTheScreen:
    """A dialog opened while another modal stands keeps the newest seed until the screen is free."""

    @pytest.fixture(name="window")
    def window_fixture(self, dpg_context: None) -> ProbeSeededWindow:
        ModalQueue.open(STANDING_TAG, lambda: None)
        window = ProbeSeededWindow(KeyRouter())
        window.open(FIRST_SEED)
        return window

    def test_a_new_seed_draws_nothing_while_the_window_waits(self, window: ProbeSeededWindow) -> None:
        window.update_view(NEWER_SEED)

        assert not window.drawn
        assert not dpg.does_item_exist(TAG)

    def test_the_window_opens_on_the_newest_seed(self, window: ProbeSeededWindow, held_frames: Frames) -> None:
        window.update_view(NEWER_SEED)

        ModalQueue.leave(STANDING_TAG)
        held_frames.render()

        assert window.drawn == [NEWER_SEED]
