from dataclasses import dataclass, field
from typing import List, Optional, Tuple

import pytest

from sampletones_application.constants.sequencer import CHANNEL_AXIS
from sampletones_application.ui.elements.table.cells import EditableCells
from sampletones_application.ui.panels.sequencer import tracker as tracker_module
from sampletones_application.ui.panels.sequencer.grid.gestures import BlockGestures
from sampletones_application.ui.panels.sequencer.input.order import (
    OrderCursor,
    OrderInputState,
)
from sampletones_application.ui.panels.sequencer.input.target import OrderTarget, TrackerTarget
from sampletones_application.ui.panels.sequencer.input.tracker import TrackerCursor, TrackerInputState
from sampletones_application.ui.panels.sequencer.order import GUISequencerOrderPanel
from sampletones_application.ui.panels.sequencer.tracker import GUISequencerTrackerPanel
from sampletones_application.utils.gui.keyboard.combination import KeyCombination
from sampletones_application.utils.gui.keyboard.event import KeyEvent
from sampletones_application.view_model.sequencer.region import (
    OrderCell,
    OrderRegion,
    TrackerCell,
    TrackerRegion,
)
from sampletones_application.view_model.sequencer.slot import TrackerSlot
from sampletones_application.view_model.sequencer.subcolumn import SubColumn
from sampletones_core.constants.enums import GeneratorName
from sampletones_shared.constants.music import OCTAVE_SEMITONES, SEMITONE_STEP
from tests.suite.grid import (
    ORDER_BLOCK_SHORTCUTS,
    TRACKER_BLOCK_SHORTCUTS,
    attach_edit_surface,
)
from tests.suite.shortcuts import shipped_source

ROW_COUNT = 64
CURSOR_ROW = 4
POSITION_COUNT = 8
CURSOR_POSITION = 2
MASTER_ROW = CHANNEL_AXIS.index(None)
PULSE1_ROW = CHANNEL_AXIS.index(GeneratorName.PULSE1)


@dataclass
class Gestures:
    """What each of the tracker's hooks was handed, which is the whole of what a press reaches the
    grid with."""

    copied: List[TrackerRegion] = field(default_factory=list)
    cut: List[TrackerRegion] = field(default_factory=list)
    deleted: List[TrackerRegion] = field(default_factory=list)
    pasted: List[TrackerCell] = field(default_factory=list)
    cleared: List[Tuple[int, Optional[GeneratorName]]] = field(default_factory=list)
    transposed: List[Tuple[TrackerRegion, int]] = field(default_factory=list)
    volume_shifted: List[Tuple[TrackerRegion, int]] = field(default_factory=list)


@dataclass
class OrderGestures:
    """What each of the order's block hooks was handed, read the same way the tracker's are."""

    copied: List[OrderRegion] = field(default_factory=list)
    cut: List[OrderRegion] = field(default_factory=list)
    deleted: List[OrderRegion] = field(default_factory=list)
    pasted: List[OrderCell] = field(default_factory=list)
    cleared: List[Tuple[GeneratorName, int, Optional[int]]] = field(default_factory=list)


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
    panel.on_adjust_transpose = lambda region, delta: gestures.transposed.append((region, delta))
    panel.on_adjust_volume = lambda region, delta: gestures.volume_shifted.append((region, delta))
    panel.can_paste_block = lambda: True
    panel._blocks = BlockGestures(grid=panel)
    attach_edit_surface(panel, TRACKER_BLOCK_SHORTCUTS, TrackerTarget)
    monkeypatch.setattr(panel, "_apply_state", lambda state: None)
    return panel


def _order_panel(
    monkeypatch: pytest.MonkeyPatch,
    gestures: OrderGestures,
    *,
    generator: Optional[GeneratorName] = GeneratorName.PULSE1,
) -> GUISequencerOrderPanel:
    """An order panel reporting the gestures it fires, with its table left unbuilt."""
    panel = GUISequencerOrderPanel.__new__(GUISequencerOrderPanel)
    panel._shortcuts = shipped_source()
    panel._input_state = OrderInputState(cursor=OrderCursor(generator, CURSOR_POSITION))
    panel._position_count = POSITION_COUNT
    panel.on_copy_block = gestures.copied.append
    panel.on_cut_block = gestures.cut.append
    panel.on_delete_block = gestures.deleted.append
    panel.on_paste_block = gestures.pasted.append
    panel.on_set_order_entry = lambda channel, position, index: gestures.cleared.append((channel, position, index))
    panel.can_paste_block = lambda: True
    panel._blocks = BlockGestures(grid=panel)
    attach_edit_surface(panel, ORDER_BLOCK_SHORTCUTS, OrderTarget)
    monkeypatch.setattr(panel, "_apply_state", lambda state, notify=True: None)
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


class TestTrackerAdjustKeys:
    """The shifts reach the same block the clipboard keys do, so a selection moves whole."""

    def test_a_selection_is_transposed_whole(self, monkeypatch: pytest.MonkeyPatch) -> None:
        gestures = Gestures()
        panel = _panel(monkeypatch, gestures)
        panel._input_state = panel._input_state.extend_row(2, ROW_COUNT)

        assert panel._on_key_pressed(_press("Ctrl+Up")) is True
        assert gestures.transposed == [
            (
                TrackerRegion(
                    first_row=CURSOR_ROW,
                    last_row=CURSOR_ROW + 2,
                    first_slot=3,
                    last_slot=3,
                ),
                SEMITONE_STEP,
            )
        ]

    def test_a_cursor_alone_shifts_the_cell_it_stands_on(self, monkeypatch: pytest.MonkeyPatch) -> None:
        gestures = Gestures()
        panel = _panel(monkeypatch, gestures, subcolumn=SubColumn.VOLUME)

        assert panel._on_key_pressed(_press("Alt+Down")) is True
        region, delta = gestures.volume_shifted[-1]
        assert region.rows == range(CURSOR_ROW, CURSOR_ROW + 1)
        assert region.slots == (TrackerSlot(GeneratorName.PULSE1, SubColumn.VOLUME),)
        assert delta == -tracker_module.VOLUME_FINE_STEP

    def test_shift_makes_the_step_the_bigger_one(self, monkeypatch: pytest.MonkeyPatch) -> None:
        gestures = Gestures()
        panel = _panel(monkeypatch, gestures)

        assert panel._on_key_pressed(_press("Ctrl+Shift+Up")) is True
        assert panel._on_key_pressed(_press("Alt+Shift+Up")) is True
        assert gestures.transposed[-1][1] == OCTAVE_SEMITONES
        assert gestures.volume_shifted[-1][1] == tracker_module.VOLUME_COARSE_STEP

    def test_a_grid_with_no_cursor_shifts_nothing(self, monkeypatch: pytest.MonkeyPatch) -> None:
        gestures = Gestures()
        panel = _panel(monkeypatch, gestures)
        panel._input_state = TrackerInputState()

        assert panel._on_key_pressed(_press("Ctrl+Up")) is False
        assert gestures.transposed == []


class TestOrderCopyKey:
    def test_a_selection_is_copied_whole(self, monkeypatch: pytest.MonkeyPatch) -> None:
        gestures = OrderGestures()
        panel = _order_panel(monkeypatch, gestures)
        panel._input_state = panel._input_state.extend_position(1, POSITION_COUNT)

        assert panel._on_key_pressed(_press("Ctrl+C")) is True
        assert gestures.copied == [
            OrderRegion(
                first_row=PULSE1_ROW,
                last_row=PULSE1_ROW,
                first_position=CURSOR_POSITION,
                last_position=CURSOR_POSITION + 1,
            )
        ]

    def test_a_cursor_alone_copies_the_cell_it_stands_on(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        gestures = OrderGestures()
        panel = _order_panel(monkeypatch, gestures, generator=None)

        assert panel._on_key_pressed(_press("Ctrl+C")) is True
        assert gestures.copied == [
            OrderRegion(
                first_row=MASTER_ROW,
                last_row=MASTER_ROW,
                first_position=CURSOR_POSITION,
                last_position=CURSOR_POSITION,
            )
        ]

    def test_a_table_with_no_cursor_copies_nothing(self, monkeypatch: pytest.MonkeyPatch) -> None:
        gestures = OrderGestures()
        panel = _order_panel(monkeypatch, gestures)
        panel._input_state = OrderInputState()

        assert panel._on_key_pressed(_press("Ctrl+C")) is False
        assert gestures.copied == []


class TestOrderCutKey:
    def test_a_selection_is_cut_whole(self, monkeypatch: pytest.MonkeyPatch) -> None:
        gestures = OrderGestures()
        panel = _order_panel(monkeypatch, gestures)
        panel._input_state = panel._input_state.extend_channel(1)

        assert panel._on_key_pressed(_press("Ctrl+X")) is True
        assert gestures.cut == [
            OrderRegion(
                first_row=PULSE1_ROW,
                last_row=PULSE1_ROW + 1,
                first_position=CURSOR_POSITION,
                last_position=CURSOR_POSITION,
            )
        ]
        assert gestures.copied == []


class TestOrderPasteKey:
    def test_a_paste_names_the_cell_the_cursor_stands_on(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        gestures = OrderGestures()
        panel = _order_panel(monkeypatch, gestures)

        assert panel._on_key_pressed(_press("Ctrl+V")) is True
        assert gestures.pasted == [OrderCell(generator=GeneratorName.PULSE1, position=CURSOR_POSITION)]

    def test_the_master_row_is_a_cell_a_block_lands_on(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        gestures = OrderGestures()
        panel = _order_panel(monkeypatch, gestures, generator=None)

        assert panel._on_key_pressed(_press("Ctrl+V")) is True
        assert gestures.pasted == [OrderCell(generator=None, position=CURSOR_POSITION)]


class TestOrderDeleteKey:
    def test_a_selection_is_deleted_whole(self, monkeypatch: pytest.MonkeyPatch) -> None:
        gestures = OrderGestures()
        panel = _order_panel(monkeypatch, gestures)
        panel._input_state = panel._input_state.extend_position(1, POSITION_COUNT)

        assert panel._on_key_pressed(_press("Del")) is True
        assert gestures.deleted == [
            OrderRegion(
                first_row=PULSE1_ROW,
                last_row=PULSE1_ROW,
                first_position=CURSOR_POSITION,
                last_position=CURSOR_POSITION + 1,
            )
        ]
        assert gestures.cleared == []

    def test_a_cursor_alone_keeps_clearing_the_cell_it_stands_on(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Delete already means something without a selection, so that meaning is what it keeps."""
        gestures = OrderGestures()
        panel = _order_panel(monkeypatch, gestures)

        assert panel._on_key_pressed(_press("Del")) is True
        assert gestures.deleted == []
        assert gestures.cleared == [(GeneratorName.PULSE1, CURSOR_POSITION, None)]
