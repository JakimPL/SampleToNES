from typing import Final, Iterator, List

import dearpygui.dearpygui as dpg
import pytest

from sampletones_application.ui.elements.layout.centered import centered

CONTENT_TAG: Final[str] = "test.centered.text.content"
COLUMN_SLOT: Final[int] = 0
CELL_SLOT: Final[int] = 1
MIDDLE: Final[int] = 1


@pytest.fixture(name="dpg_context")
def dpg_context_fixture() -> Iterator[None]:
    dpg.create_context()
    try:
        yield
    finally:
        dpg.destroy_context()


def build() -> int:
    """Builds one centered item and returns the table standing around it."""
    with dpg.window():
        with centered():
            dpg.add_text("content", tag=CONTENT_TAG)

    group = dpg.get_item_parent(CONTENT_TAG)
    row = dpg.get_item_parent(group)
    return dpg.get_item_parent(row)


class TestCentered:
    """``centered`` stands the block's content in a fitted column between two equal ones."""

    def test_the_content_sits_in_the_middle_cell(self, dpg_context: None) -> None:
        table = build()
        row = dpg.get_item_children(table, CELL_SLOT)[0]
        cells: List[int] = dpg.get_item_children(row, CELL_SLOT)
        assert cells.index(dpg.get_item_parent(CONTENT_TAG)) == MIDDLE

    def test_the_middle_column_fits_its_content(self, dpg_context: None) -> None:
        columns: List[int] = dpg.get_item_children(build(), COLUMN_SLOT)
        assert dpg.get_item_configuration(columns[MIDDLE])["width_fixed"]

    def test_the_flanking_columns_share_the_rest_equally(self, dpg_context: None) -> None:
        columns: List[int] = dpg.get_item_children(build(), COLUMN_SLOT)
        left = dpg.get_item_configuration(columns[0])
        right = dpg.get_item_configuration(columns[-1])
        assert left["width_stretch"] and right["width_stretch"]
        assert left["init_width_or_weight"] == right["init_width_or_weight"]
