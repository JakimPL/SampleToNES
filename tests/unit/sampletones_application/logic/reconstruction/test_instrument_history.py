from typing import Final, List
from unittest.mock import MagicMock

import pytest

from sampletones_application.logic.history.action import HistoryAction
from sampletones_application.logic.history.manager import HistoryManager
from sampletones_application.logic.project.controller import ProjectController
from sampletones_application.logic.project.manager import ProjectManager
from sampletones_application.logic.reconstruction.editor import InstrumentEditor
from sampletones_application.logic.reconstruction.manager import ReconstructionManager
from sampletones_application.view_model.shared.history import (
    HistoryDetail,
    HistoryDetailRole,
    HistoryDetailSegment,
)
from sampletones_core.constants.enums import FeatureKey
from sampletones_core.features.envelope import Envelope
from sampletones_core.project.voices.creation import new_instrument
from sampletones_core.project.voices.instrument import Instrument

HISTORY_BUDGET: Final[int] = 16
VOLUME_LETTER: Final[str] = "V"


class _Harness:
    """The tab's write boundary over a strict history, which is how the application builds it."""

    def __init__(self) -> None:
        self.controller = ProjectController(ProjectManager())
        self.history = HistoryManager(self.controller, budget=HISTORY_BUDGET, strict=True)
        self.controller.on_mutation = self.history.handle_mutation
        self.controller.new()

        self.details: List[str] = []
        reconstruction_manager = MagicMock(spec=ReconstructionManager)
        reconstruction_manager.current_features = None
        self.editor = InstrumentEditor(
            reconstruction_manager,
            self.controller,
            self.history,
            self._detail,
        )

    def _detail(self, voice_id: str, feature_key: FeatureKey) -> HistoryDetail:
        self.details.append(f"{voice_id}:{feature_key.value}")
        return (
            HistoryDetailSegment(text=voice_id, role=HistoryDetailRole.INSTRUMENT),
            HistoryDetailSegment(text=VOLUME_LETTER, role=HistoryDetailRole.FEATURE_VOLUME),
        )

    def open_instrument(self, name: str = "lead") -> Instrument:
        """Adds a voice and puts it in front of the tab, as the pool and the tab each do."""
        with self.history.transaction(HistoryAction.ADD_INSTRUMENT):
            instrument = self.controller.add_instrument(new_instrument(name))

        self.editor.edit_instrument(instrument.id)
        return instrument

    def write(self, feature_key: FeatureKey, *items: int) -> None:
        self.editor.write_envelope(feature_key, Envelope[int](items=items))


@pytest.fixture
def harness() -> _Harness:
    return _Harness()


class TestAnInstrumentEditInTheHistory:
    def test_an_edit_is_recorded_as_the_edit_it_is(self, harness: _Harness) -> None:
        """A write outside a transaction would be reported by the strict history instead."""
        harness.open_instrument()

        harness.write(FeatureKey.VOLUME, 15, 12, 9)

        assert [entry.action for entry in harness.history.entries[1:]] == [HistoryAction.EDIT_INSTRUMENT]

    def test_the_entry_names_the_voice_and_the_dimension_it_moved(self, harness: _Harness) -> None:
        instrument = harness.open_instrument()

        harness.write(FeatureKey.VOLUME, 15)

        assert harness.details == [f"{instrument.id}:{FeatureKey.VOLUME.value}"]
        assert harness.history.entries[-1].detail[-1].text == VOLUME_LETTER

    def test_a_drag_across_one_dimension_is_undone_in_one_step(self, harness: _Harness) -> None:
        harness.open_instrument()

        for level in (15, 14, 13, 12):
            harness.write(FeatureKey.VOLUME, level)

        assert [entry.action for entry in harness.history.entries[1:]] == [HistoryAction.EDIT_INSTRUMENT]

    def test_undoing_that_drag_returns_the_envelope_it_started_from(self, harness: _Harness) -> None:
        instrument = harness.open_instrument()
        started_from = harness.controller.project.voices[instrument.id].envelopes.volume

        for level in (15, 14, 13, 12):
            harness.write(FeatureKey.VOLUME, level)

        harness.history.undo()

        assert harness.controller.project.voices[instrument.id].envelopes.volume == started_from

    def test_two_dimensions_are_two_entries(self, harness: _Harness) -> None:
        """Each dimension is its own target, so moving one leaves the other's entry standing."""
        harness.open_instrument()

        harness.write(FeatureKey.VOLUME, 15)
        harness.write(FeatureKey.ARPEGGIO, 0, 4, 7)

        assert [entry.action for entry in harness.history.entries[1:]] == [
            HistoryAction.EDIT_INSTRUMENT,
            HistoryAction.EDIT_INSTRUMENT,
        ]

    def test_two_voices_are_two_entries(self, harness: _Harness) -> None:
        harness.open_instrument("lead")
        harness.write(FeatureKey.VOLUME, 15)

        harness.open_instrument("bass")
        harness.write(FeatureKey.VOLUME, 15)

        assert [entry.action for entry in harness.history.entries[1:]].count(HistoryAction.EDIT_INSTRUMENT) == 2

    def test_writing_with_no_instrument_open_is_refused(self, harness: _Harness) -> None:
        with pytest.raises(RuntimeError):
            harness.write(FeatureKey.VOLUME, 15)
