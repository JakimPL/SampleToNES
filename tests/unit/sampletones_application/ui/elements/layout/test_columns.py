from dataclasses import dataclass
from typing import Iterator, Tuple

import dearpygui.dearpygui as dpg
import pytest

from sampletones_application.tags.compose import compose_tag
from sampletones_application.tags.general import SUF_TABLE_COLUMN, SUF_TABLE_GAP
from sampletones_application.ui.elements.layout.columns import ColumnSpec, TabColumns
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase

_PANEL_GAP = 12
_LEFT = "test.left"
_MIDDLE = "test.middle"
_RIGHT = "test.right"


@pytest.fixture
def dpg_context() -> Iterator[None]:
    dpg.create_context()
    try:
        yield
    finally:
        dpg.destroy_context()


def _fill(parent: str) -> None:
    dpg.add_text("card", parent=parent)


def _columns(*tags: str) -> Tuple[ColumnSpec, ...]:
    return tuple(ColumnSpec(tag=tag, build=_fill) for tag in tags)


def _weight(tag: str) -> float:
    return float(dpg.get_item_configuration(compose_tag(tag, SUF_TABLE_COLUMN))["init_width_or_weight"])


def _gap(tag: str) -> float:
    return float(dpg.get_item_configuration(compose_tag(tag, SUF_TABLE_GAP))["init_width_or_weight"])


class TestARowDeclaresWhatItsColumnsTake(BaseTestSuite):
    """A row states each column's share rather than reading it back from the card inside it, so the
    proportions hold whatever its cards draw and a column put away can come back at the share it
    was declared with."""

    def test_a_stretching_column_takes_a_share_of_its_own(self, dpg_context: None) -> None:
        with dpg.window():
            TabColumns.row(panel_gap=_PANEL_GAP, columns=_columns(_LEFT, _RIGHT))

        assert _weight(_LEFT) == _weight(_RIGHT)
        assert _weight(_LEFT) > 0

    def test_a_fixed_column_takes_the_width_it_names(self, dpg_context: None) -> None:
        with dpg.window():
            TabColumns.row(
                panel_gap=_PANEL_GAP,
                columns=(
                    ColumnSpec(tag=_LEFT, build=_fill, width=240),
                    ColumnSpec(tag=_RIGHT, build=_fill),
                ),
            )

        assert _weight(_LEFT) == 240

    def test_a_gap_stands_between_neighbors(self, dpg_context: None) -> None:
        with dpg.window():
            TabColumns.row(panel_gap=_PANEL_GAP, columns=_columns(_LEFT, _RIGHT))

        assert _gap(_RIGHT) == _PANEL_GAP


class TestARowDividesItselfAmongTheColumnsStanding(BaseTestSuite):
    """A card the reader puts away leaves its column nothing to hold, so the row gives its share to
    the columns still standing and keeps one gap between each of them."""

    @dataclass(frozen=True, kw_only=True)
    class StandingCase(BaseRegularTestCase):
        declared: Tuple[str, ...]
        standing: Tuple[str, ...]
        expected_weights: Tuple[float, ...]
        expected_gaps: Tuple[float, ...]

    test_cases = (
        StandingCase(
            label="both_stand",
            declared=(_LEFT, _RIGHT),
            standing=(_LEFT, _RIGHT),
            expected_weights=(1.0, 1.0),
            expected_gaps=(_PANEL_GAP,),
        ),
        StandingCase(
            label="the_last_is_put_away",
            declared=(_LEFT, _RIGHT),
            standing=(_LEFT,),
            expected_weights=(1.0, 0.0),
            expected_gaps=(0.0,),
        ),
        StandingCase(
            label="the_first_is_put_away",
            declared=(_LEFT, _RIGHT),
            standing=(_RIGHT,),
            expected_weights=(0.0, 1.0),
            expected_gaps=(0.0,),
        ),
        StandingCase(
            label="the_middle_is_put_away",
            declared=(_LEFT, _MIDDLE, _RIGHT),
            standing=(_LEFT, _RIGHT),
            expected_weights=(1.0, 0.0, 1.0),
            expected_gaps=(0.0, _PANEL_GAP),
        ),
        StandingCase(
            label="every_column_is_put_away",
            declared=(_LEFT, _RIGHT),
            standing=(),
            expected_weights=(0.0, 0.0),
            expected_gaps=(0.0,),
        ),
    )

    @pytest.mark.parametrize("case", test_cases, ids=lambda case: case.label)
    def test_the_row_holds_what_stands(self, case: StandingCase, dpg_context: None) -> None:
        columns = _columns(*case.declared)
        with dpg.window():
            TabColumns.row(panel_gap=_PANEL_GAP, columns=columns)

        TabColumns.stand_columns(columns, frozenset(case.standing), _PANEL_GAP)

        assert tuple(_weight(tag) for tag in case.declared) == case.expected_weights
        assert tuple(_gap(tag) for tag in case.declared[1:]) == case.expected_gaps

    def test_a_column_comes_back_at_the_share_it_was_declared_with(self, dpg_context: None) -> None:
        columns = _columns(_LEFT, _RIGHT)
        with dpg.window():
            TabColumns.row(panel_gap=_PANEL_GAP, columns=columns)

        TabColumns.stand_columns(columns, frozenset({_LEFT}), _PANEL_GAP)
        TabColumns.stand_columns(columns, frozenset({_LEFT, _RIGHT}), _PANEL_GAP)

        assert _weight(_LEFT) == _weight(_RIGHT)
        assert _gap(_RIGHT) == _PANEL_GAP
