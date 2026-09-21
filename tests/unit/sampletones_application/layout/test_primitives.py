from typing import Final

from sampletones_application.layout.primitives import DEARPYGUI_MAXIMUM_WINDOW_SIZE, DialogGeometry

STATED_HEIGHT: Final[int] = 210
STATED_WIDTH: Final[int] = 480


class TestTheSizeADialogIsHeldTo:
    """A dialog reads at the width it states and grows down to hold what it holds.

    A window free to widen to its content, holding content that measures itself against the
    window's width, hands each a little more every frame until the screen stops it.
    """

    def test_the_width_a_dialog_opens_at_is_the_width_it_stops_at(self) -> None:
        geometry = DialogGeometry(width=STATED_WIDTH, height=STATED_HEIGHT)

        assert geometry.minimum_size[0] == geometry.maximum_size[0] == STATED_WIDTH

    def test_a_dialog_stating_no_height_holds_its_width_all_the_same(self) -> None:
        geometry = DialogGeometry(width=STATED_WIDTH)

        assert geometry.minimum_size[0] == geometry.maximum_size[0] == STATED_WIDTH

    def test_the_height_a_dialog_opens_at_is_the_least_it_takes(self) -> None:
        geometry = DialogGeometry(width=STATED_WIDTH, height=STATED_HEIGHT)

        assert geometry.minimum_size[1] == STATED_HEIGHT
        assert geometry.maximum_size[1] == DEARPYGUI_MAXIMUM_WINDOW_SIZE

    def test_a_dialog_stating_no_height_starts_from_its_content(self) -> None:
        geometry = DialogGeometry(width=STATED_WIDTH)

        assert geometry.minimum_size[1] == 0
        assert geometry.maximum_size[1] == DEARPYGUI_MAXIMUM_WINDOW_SIZE
