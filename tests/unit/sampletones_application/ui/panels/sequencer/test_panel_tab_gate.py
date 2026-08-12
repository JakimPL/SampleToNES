from dataclasses import dataclass
from typing import Callable, Union

import pytest

from sampletones_application.ui.panels.sequencer.input.order import (
    OrderCursor,
    OrderInputState,
)
from sampletones_application.ui.panels.sequencer.input.tracker import TrackerCursor, TrackerInputState
from sampletones_application.ui.panels.sequencer.order import GUISequencerOrderPanel
from sampletones_application.ui.panels.sequencer.samples import GUISequencerSamplesPanel
from sampletones_application.ui.panels.sequencer.tracker import GUISequencerTrackerPanel
from sampletones_application.utils.gui.keyboard import ActivePredicate, KeyRouter, focus
from sampletones_application.view_model.sequencer.subcolumn import SubColumn
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase

SequencerPanel = Union[
    GUISequencerTrackerPanel,
    GUISequencerOrderPanel,
    GUISequencerSamplesPanel,
]

SELECTED_ID = "bass-id"


@pytest.fixture(autouse=True)
def no_focused_field(monkeypatch: pytest.MonkeyPatch) -> None:
    """No text field is being edited, so the tab is the only thing holding a key back."""
    monkeypatch.setattr(focus, "is_field_focused", lambda: False)


def _tracker(tab_active: ActivePredicate) -> GUISequencerTrackerPanel:
    """A tracker grid holding a cursor, which is what it keeps across a move to another tab."""
    panel = GUISequencerTrackerPanel.__new__(GUISequencerTrackerPanel)
    panel._router = KeyRouter()
    panel._tab_active = tab_active
    panel._input_state = TrackerInputState(cursor=TrackerCursor(0, None, SubColumn.INSTRUMENT))
    return panel


def _order(tab_active: ActivePredicate) -> GUISequencerOrderPanel:
    """An order table holding a cursor, which is what it keeps across a move to another tab."""
    panel = GUISequencerOrderPanel.__new__(GUISequencerOrderPanel)
    panel._router = KeyRouter()
    panel._tab_active = tab_active
    panel._input_state = OrderInputState(cursor=OrderCursor(None, 0))
    return panel


def _samples(tab_active: ActivePredicate) -> GUISequencerSamplesPanel:
    """A samples panel holding a selection, which is what it keeps across a move to another tab."""
    panel = GUISequencerSamplesPanel.__new__(GUISequencerSamplesPanel)
    panel._router = KeyRouter()
    panel._tab_active = tab_active
    panel._selected_sample_id = SELECTED_ID
    panel._editing_sample_id = None
    return panel


def _renaming_samples(tab_active: ActivePredicate) -> GUISequencerSamplesPanel:
    """A samples panel mid-rename, the one state that keeps the keyboard on its own tab."""
    panel = _samples(tab_active)
    panel._editing_sample_id = SELECTED_ID
    return panel


class TestPanelKeysFollowTheTabInFront(BaseTestSuite):
    """A sequencer panel answers the keyboard while the Sequencer is the tab in front.

    Each panel keeps its cursor or selection while another tab is worked on, so the tab is what
    tells a press meant for the song from one meant for whatever stands in front of it.
    """

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        build: Callable[[ActivePredicate], SequencerPanel]

    test_cases = (
        TestCase(label="the tracker grid holds a cursor", build=_tracker),
        TestCase(label="the order table holds a cursor", build=_order),
        TestCase(label="the samples panel holds a selection", build=_samples),
        TestCase(label="the samples panel is mid-rename", build=_renaming_samples),
    )

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_a_panel_stands_down_while_another_tab_is_in_front(self, test_case: TestCase) -> None:
        panel = test_case.build(lambda: False)

        assert panel._keys_active() is False

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_a_panel_answers_while_its_own_tab_is_in_front(self, test_case: TestCase) -> None:
        panel = test_case.build(lambda: True)

        assert panel._keys_active() is True
