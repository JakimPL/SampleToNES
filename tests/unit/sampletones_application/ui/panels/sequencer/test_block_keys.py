from dataclasses import dataclass, field
from typing import List, Optional, Tuple

import pytest

from sampletones_application.ui.elements.table.cells import EditableCells
from sampletones_application.ui.panels.sequencer.input.cursor import TrackerCursor
from sampletones_application.ui.panels.sequencer.input.state import TrackerInputState
from sampletones_application.ui.panels.sequencer.tracker import GUISequencerTrackerPanel
from sampletones_application.utils.gui.keyboard.combination import KeyCombination
from sampletones_application.utils.gui.keyboard.event import KeyEvent
from sampletones_application.view_model.sequencer.region import TrackerCell, TrackerRegion
from sampletones_application.view_model.sequencer.slot import TrackerSlot
from sampletones_application.view_model.sequencer.subcolumn import SubColumn
from sampletones_core.constants.enums import GeneratorName
from tests.suite.shortcuts import shipped_source

ROW_COUNT = 64
CURSOR_ROW = 4


@dataclass
class Gestures:
    """What each block hook was handed, which is the whole of what a press reaches the grid with."""

    copied: List[TrackerRegion] = field(default_factory=list)
    cut: List[TrackerRegion] = field(default_factory=list)
    deleted: List[TrackerRegion] = field(default_factory=list)
    pasted: List[TrackerCell] = field(default_factory=list)
    cleared: List[Tuple[int, Optional[GeneratorName]]] = field(default_factory=list)


def _press(text: str) -> KeyEvent:
    """The press a written combination names, as the router delivers it."""
    combination = KeyCombination.parse(text)
    return KeyEvent(key=combination.key, modifiers=combination.modifiers)


def _panel(
    monkeypatch: pytest.MonkeyPatch,
    gestures: Gestures,
    *,
    generator: Optional[GeneratorName] = GeneratorName.PULSE1,
    subcolumn: SubColumn = SubColumn.INSTRUMENT,
) -> GUISequencerTrackerPanel:
    """A tracker panel reporting the gestures it fires, with its grid left unbuilt.

    Applying a state draws into DearPyGui, which has no table here, so the draw is left out and
    each gesture is read from what its hook receives.
    """
    panel = GUISequencerTrackerPanel.__new__(GUISequencerTrackerPanel)
    panel._shortcuts = shipped_source()
    panel._input_state = TrackerInputState(cursor=TrackerCursor(CURSOR_ROW, generator, subcolumn))
    panel._current_row_count = ROW_COUNT
    panel._editable_cells = EditableCells()
    panel.on_copy_block = gestures.copied.append
    panel.on_cut_block = gestures.cut.append
    panel.on_delete_block = gestures.deleted.append
    panel.on_paste_block = gestures.pasted.append
    panel.on_clear_row = lambda row, generator_name: gestures.cleared.append((row, generator_name))
    monkeypatch.setattr(panel, "_apply_state", lambda state: None)
    return panel


class TestTrackerCopyKey:
    def test_a_selection_is_copied_whole(self, monkeypatch: pytest.MonkeyPatch) -> None:
        gestures = Gestures()
        panel = _panel(monkeypatch, gestures)
        panel._input_state = panel._input_state.extend_row(2, ROW_COUNT)

        assert panel._on_key_pressed(_press("Ctrl+C")) is True
        assert gestures.copied == [
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
        gestures = Gestures()
        panel = _panel(monkeypatch, gestures, subcolumn=SubColumn.VOLUME)

        assert panel._on_key_pressed(_press("Ctrl+C")) is True
        assert gestures.copied[-1].rows == range(CURSOR_ROW, CURSOR_ROW + 1)
        assert gestures.copied[-1].slots == (TrackerSlot(GeneratorName.PULSE1, SubColumn.VOLUME),)

    def test_a_grid_with_no_cursor_copies_nothing(self, monkeypatch: pytest.MonkeyPatch) -> None:
        gestures = Gestures()
        panel = _panel(monkeypatch, gestures)
        panel._input_state = TrackerInputState()

        assert panel._on_key_pressed(_press("Ctrl+C")) is False
        assert gestures.copied == []


class TestTrackerCutKey:
    def test_a_selection_is_cut_whole(self, monkeypatch: pytest.MonkeyPatch) -> None:
        gestures = Gestures()
        panel = _panel(monkeypatch, gestures)
        panel._input_state = panel._input_state.extend_row(2, ROW_COUNT)

        assert panel._on_key_pressed(_press("Ctrl+X")) is True
        assert gestures.cut == [
            TrackerRegion(
                first_row=CURSOR_ROW,
                last_row=CURSOR_ROW + 2,
                first_slot=3,
                last_slot=3,
            )
        ]
        assert gestures.copied == []


class TestTrackerPasteKey:
    def test_a_paste_names_the_cell_the_cursor_stands_on(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """The cell carries a row and a column alone, so the subcolumn under the cursor is left
        for the block to decide."""
        gestures = Gestures()
        panel = _panel(monkeypatch, gestures, subcolumn=SubColumn.VOLUME)

        assert panel._on_key_pressed(_press("Ctrl+V")) is True
        assert gestures.pasted == [TrackerCell(row=CURSOR_ROW, generator=GeneratorName.PULSE1)]

    def test_the_sample_column_is_a_cell_a_block_lands_on(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        gestures = Gestures()
        panel = _panel(monkeypatch, gestures, generator=None)

        assert panel._on_key_pressed(_press("Ctrl+V")) is True
        assert gestures.pasted == [TrackerCell(row=CURSOR_ROW, generator=None)]


class TestTrackerDeleteKey:
    def test_a_selection_is_deleted_whole(self, monkeypatch: pytest.MonkeyPatch) -> None:
        gestures = Gestures()
        panel = _panel(monkeypatch, gestures)
        panel._input_state = panel._input_state.extend_row(2, ROW_COUNT)

        assert panel._on_key_pressed(_press("Del")) is True
        assert gestures.deleted == [
            TrackerRegion(
                first_row=CURSOR_ROW,
                last_row=CURSOR_ROW + 2,
                first_slot=3,
                last_slot=3,
            )
        ]
        assert gestures.cleared == []

    def test_a_cursor_alone_keeps_clearing_the_cell_it_stands_on(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Delete already means something without a selection, so that meaning is what it keeps."""
        gestures = Gestures()
        panel = _panel(monkeypatch, gestures)

        assert panel._on_key_pressed(_press("Del")) is True
        assert gestures.deleted == []
        assert gestures.cleared == [(CURSOR_ROW, GeneratorName.PULSE1)]
