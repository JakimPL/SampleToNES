from typing import Optional

from sampletones_application.ui.panels.sequencer.input.cursor import TrackerCursor
from sampletones_application.ui.panels.sequencer.input.state import TrackerInputState
from sampletones_application.view_model.sequencer.subcolumn import SubColumn
from sampletones_core.constants.enums import GeneratorName


def _state(
    subcolumn: SubColumn,
    *,
    row: int = 0,
    generator: Optional[GeneratorName] = GeneratorName.PULSE1,
    pending: str = "",
) -> TrackerInputState:
    return TrackerInputState(cursor=TrackerCursor(row, generator, subcolumn), pending=pending)


class TestNoteOffEntry:
    def test_minus_in_instrument_emits_note_off(self) -> None:
        state, action = _state(SubColumn.INSTRUMENT).type_char("-")
        assert action is not None
        assert action.note_off is True
        assert action.row == 0
        assert action.generator == GeneratorName.PULSE1
        assert state.pending == ""

    def test_plus_in_instrument_is_ignored(self) -> None:
        state = _state(SubColumn.INSTRUMENT)
        new_state, action = state.type_char("+")
        assert action is None
        assert new_state is state

    def test_minus_in_transpose_is_a_sign_not_note_off(self) -> None:
        new_state, action = _state(SubColumn.TRANSPOSE).type_char("-")
        assert action is None
        assert new_state.pending.startswith("-")


class TestColumnNavigation:
    def test_tab_preserves_subcolumn(self) -> None:
        state = _state(SubColumn.VOLUME, generator=GeneratorName.PULSE1)
        moved = state.navigate_column_by(1)
        assert moved.cursor is not None
        assert moved.cursor.generator != GeneratorName.PULSE1
        assert moved.cursor.subcolumn is SubColumn.VOLUME

    def test_shift_tab_preserves_subcolumn(self) -> None:
        state = _state(SubColumn.TRANSPOSE, generator=GeneratorName.PULSE1)
        moved = state.navigate_column_by(-1)
        assert moved.cursor is not None
        assert moved.cursor.subcolumn is SubColumn.TRANSPOSE

    def test_tab_preserves_row(self) -> None:
        state = _state(SubColumn.VOLUME, row=5, generator=GeneratorName.PULSE1)
        moved = state.navigate_column_by(1)
        assert moved.cursor is not None
        assert moved.cursor.row == 5
