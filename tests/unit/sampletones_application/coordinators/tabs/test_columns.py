from typing import List
from unittest.mock import MagicMock

from sampletones_application.coordinators.tabs.columns import persisting_collapse, side_column
from sampletones_application.parameters.geometry import TabGeometry
from sampletones_application.tags.general import TAG_GLOBAL_THEME_PANEL_SURFACE

CARD_TAG = "card"
COLUMN_TAG = "column"


class TestACollapseHandlerPersistsTheCard:
    """A collapse is kept for the next launch before the column around the card reflows."""

    def test_the_state_is_kept_then_the_column_reflows(self) -> None:
        events: List[str] = []
        session_manager = MagicMock()
        session_manager.set_card_collapsed.side_effect = lambda tag, collapsed: events.append(f"{tag}:{collapsed}")

        handler = persisting_collapse(session_manager, then=lambda: events.append("reflowed"))
        handler(CARD_TAG, True)
        handler(CARD_TAG, False)

        assert events == [f"{CARD_TAG}:True", "reflowed", f"{CARD_TAG}:False", "reflowed"]

    def test_a_card_with_no_reflow_is_kept_alone(self) -> None:
        session_manager = MagicMock()

        persisting_collapse(session_manager, then=None)(CARD_TAG, True)

        session_manager.set_card_collapsed.assert_called_once_with(CARD_TAG, True)


class TestASideColumn:
    def test_the_column_is_one_raised_surface_at_the_shared_side_size(self) -> None:
        geometry = TabGeometry(
            side_width=310, side_height=640, center_weight=3, baseline_viewport_width=1600, rail_width=24, panel_gap=8
        )
        build = MagicMock()

        column = side_column(geometry, tag=COLUMN_TAG, build=build)

        assert (column.tag, column.build, column.theme) == (COLUMN_TAG, build, TAG_GLOBAL_THEME_PANEL_SURFACE)
        assert (column.width, column.height, column.no_scrollbar) == (geometry.side_width, geometry.side_height, True)
        assert not column.stretches
