from typing import List, Optional

import pytest

from sampletones_application.ui.panels.sequencer.input.cursor import TrackerCursor
from sampletones_application.ui.panels.sequencer.input.state import TrackerInputState
from sampletones_application.ui.panels.sequencer.tracker import GUISequencerTrackerPanel
from sampletones_application.utils.gui.keyboard.combination import KeyCombination
from sampletones_application.utils.gui.keyboard.event import KeyEvent
from sampletones_application.view_model.sequencer.region import TrackerRegion
from sampletones_application.view_model.sequencer.slot import TrackerSlot
from sampletones_application.view_model.sequencer.subcolumn import SubColumn
from sampletones_core.constants.enums import GeneratorName
from tests.suite.shortcuts import shipped_source

ROW_COUNT = 64
CURSOR_ROW = 4


def _press(text: str) -> KeyEvent:
    """The press a written combination names, as the router delivers it."""
    combination = KeyCombination.parse(text)
    return KeyEvent(key=combination.key, modifiers=combination.modifiers)


def _panel(
    monkeypatch: pytest.MonkeyPatch,
    regions: List[TrackerRegion],
    *,
    generator: Optional[GeneratorName] = GeneratorName.PULSE1,
    subcolumn: SubColumn = SubColumn.INSTRUMENT,
) -> GUISequencerTrackerPanel:
    """A tracker panel reporting the blocks it copies, with its grid left unbuilt.

    Applying a state draws into DearPyGui, which has no table here, so the draw is left out and
    the gesture is read from the regions the copy hook receives.
    """
    panel = GUISequencerTrackerPanel.__new__(GUISequencerTrackerPanel)
    panel._shortcuts = shipped_source()
    panel._input_state = TrackerInputState(cursor=TrackerCursor(CURSOR_ROW, generator, subcolumn))
    panel._current_row_count = ROW_COUNT
    panel.on_copy_block = regions.append
    monkeypatch.setattr(panel, "_apply_state", lambda state: None)
    return panel


class TestTrackerCopyKey:
    def test_a_selection_is_copied_whole(self, monkeypatch: pytest.MonkeyPatch) -> None:
        regions: List[TrackerRegion] = []
        panel = _panel(monkeypatch, regions)
        panel._input_state = panel._input_state.extend_row(2, ROW_COUNT)

        assert panel._on_key_pressed(_press("Ctrl+C")) is True
        assert regions == [
            TrackerRegion(
                first_row=CURSOR_ROW,
                last_row=CURSOR_ROW + 2,
                first_slot=3,
                last_slot=3,
            )
        ]

    def test_a_cursor_alone_copies_the_cell_it_stands_on(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        regions: List[TrackerRegion] = []
        panel = _panel(monkeypatch, regions, subcolumn=SubColumn.VOLUME)

        assert panel._on_key_pressed(_press("Ctrl+C")) is True
        assert regions[-1].rows == range(CURSOR_ROW, CURSOR_ROW + 1)
        assert regions[-1].slots == (TrackerSlot(GeneratorName.PULSE1, SubColumn.VOLUME),)

    def test_a_grid_with_no_cursor_copies_nothing(self, monkeypatch: pytest.MonkeyPatch) -> None:
        regions: List[TrackerRegion] = []
        panel = _panel(monkeypatch, regions)
        panel._input_state = TrackerInputState()

        assert panel._on_key_pressed(_press("Ctrl+C")) is False
        assert regions == []
