from typing import Any, Final, Iterator, Optional

import dearpygui.dearpygui as dpg
import pytest

from sampletones_application.ui.elements.window import GUIWindow
from sampletones_shared.types.callback import VoidCallback

TAG: Final[str] = "test.dialog.window.probe"
STATED_WIDTH: Final[int] = 460
CONTENT_HEIGHT: Final[int] = 0


class ProbeWindow(GUIWindow):
    """A dialog whose content stretches across the window, the shape a stated width has to hold."""

    def __init__(self, on_close: Optional[VoidCallback]) -> None:
        self._on_close = on_close
        super().__init__(
            tag=TAG,
            width=STATED_WIDTH,
            height=CONTENT_HEIGHT,
        )

    def prepare(self, *_args: Any, **_kwargs: Any) -> None:
        """The probe carries no state to seed."""

    def create_window(self) -> None:
        with self.dialog_window(
            label="probe",
            on_close=self._on_close,
        ):
            dpg.add_combo(items=["a", "b"], width=-1)


@pytest.fixture(name="dpg_context")
def dpg_context_fixture() -> Iterator[None]:
    dpg.create_context()
    try:
        yield
    finally:
        dpg.destroy_context()


class TestDialogGeometry:
    def test_the_window_holds_the_width_it_states(self, dpg_context: None) -> None:
        ProbeWindow(on_close=None).create_window()

        assert dpg.get_item_configuration(TAG)["width"] == STATED_WIDTH

    def test_the_window_takes_no_size_from_its_content(self, dpg_context: None) -> None:
        """A window measuring itself against stretched content loses a pixel of width every frame."""
        ProbeWindow(on_close=None).create_window()

        assert dpg.get_item_configuration(TAG)["autosize"] is False


class TestCloseAffordance:
    def test_a_dialog_answering_for_its_close_offers_the_button(self, dpg_context: None) -> None:
        ProbeWindow(on_close=lambda: None).create_window()

        assert dpg.get_item_configuration(TAG)["no_close"] is False

    def test_a_dialog_answering_for_no_close_omits_the_button(self, dpg_context: None) -> None:
        ProbeWindow(on_close=None).create_window()

        assert dpg.get_item_configuration(TAG)["no_close"] is True
