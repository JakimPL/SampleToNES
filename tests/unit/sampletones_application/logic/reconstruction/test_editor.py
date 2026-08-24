from typing import Final, Tuple
from unittest.mock import MagicMock

import pytest

from sampletones_application.logic.history.manager import HistoryManager
from sampletones_application.logic.project.controller import ProjectController
from sampletones_application.logic.project.manager import ProjectManager
from sampletones_application.logic.reconstruction.editing import InstrumentEdit, ReconstructionEdit
from sampletones_application.logic.reconstruction.editor import InstrumentEditor
from sampletones_application.logic.reconstruction.manager import ReconstructionManager
from sampletones_core.constants.enums import ChannelName, FeatureKey
from sampletones_core.exporters import Features
from sampletones_core.features.envelope import Envelope
from sampletones_core.project.voices.creation import SUSTAINING_ENVELOPES, new_instrument
from sampletones_core.project.voices.instrument import Instrument

ROOT_PITCH: Final[int] = 55
VOLUME: Final[Tuple[int, ...]] = (15, 12, 9)


def _features() -> Features:
    return Features(
        initial_pitch=ROOT_PITCH,
        volume=Envelope(items=(15,)),
        arpeggio=Envelope(items=(0,)),
        pitch=None,
        hi_pitch=None,
        duty_cycle=None,
    )


@pytest.fixture
def controller() -> ProjectController:
    return ProjectController(ProjectManager())


@pytest.fixture
def reconstruction_manager() -> MagicMock:
    manager = MagicMock(spec=ReconstructionManager)
    manager.current_features = None
    return manager


HISTORY_BUDGET: Final[int] = 16


@pytest.fixture
def history(controller: ProjectController) -> HistoryManager:
    """A strict history, so an edit landing outside a transaction is reported rather than healed."""
    return HistoryManager(controller, budget=HISTORY_BUDGET, strict=True)


@pytest.fixture
def editor(
    reconstruction_manager: MagicMock,
    controller: ProjectController,
    history: HistoryManager,
) -> InstrumentEditor:
    return InstrumentEditor(reconstruction_manager, controller, history, lambda _voice_id, _feature_key: ())


class TestWhatTheTabHasInFront:
    def test_it_holds_nothing_to_begin_with(self, editor: InstrumentEditor) -> None:
        assert editor.edited_instrument() is None

    def test_a_loaded_reconstruction_answers_with_its_channels(
        self,
        editor: InstrumentEditor,
        reconstruction_manager: MagicMock,
    ) -> None:
        reconstruction_manager.current_features = MagicMock(channels={ChannelName.PULSE1: _features()})

        edit = editor.edited_instrument()

        assert isinstance(edit, ReconstructionEdit)
        assert list(edit.channels) == [ChannelName.PULSE1]

    def test_an_instrument_answers_with_what_it_states(
        self,
        editor: InstrumentEditor,
        controller: ProjectController,
    ) -> None:
        """The pitch an export reads travels inside the envelopes the tab has in front of it."""
        instrument = controller.add_instrument(
            Instrument(name="lead", envelopes=SUSTAINING_ENVELOPES, initial_pitch=ROOT_PITCH)
        )

        editor.edit_instrument(instrument.id)

        edit = editor.edited_instrument()
        assert isinstance(edit, InstrumentEdit)
        assert (edit.voice_id, edit.name) == (instrument.id, "lead")
        assert edit.features.initial_pitch == ROOT_PITCH

    def test_opening_an_instrument_closes_the_reconstruction_the_tab_held(
        self,
        editor: InstrumentEditor,
        controller: ProjectController,
        reconstruction_manager: MagicMock,
    ) -> None:
        """The tab describes one voice, so its waveform and stems follow what is in front of it."""
        instrument = controller.add_instrument(new_instrument("lead"))

        editor.edit_instrument(instrument.id)

        reconstruction_manager.close_reconstruction.assert_called_once_with()

    def test_letting_go_of_an_instrument_hands_the_tab_back(
        self,
        editor: InstrumentEditor,
        controller: ProjectController,
        reconstruction_manager: MagicMock,
    ) -> None:
        instrument = controller.add_instrument(new_instrument("lead"))
        editor.edit_instrument(instrument.id)
        reconstruction_manager.current_features = MagicMock(channels={ChannelName.PULSE1: _features()})

        editor.release_instrument()

        assert isinstance(editor.edited_instrument(), ReconstructionEdit)

    def test_an_instrument_removed_from_the_project_leaves_the_tab_holding_nothing(
        self,
        editor: InstrumentEditor,
        controller: ProjectController,
    ) -> None:
        instrument = controller.add_instrument(new_instrument("lead"))
        editor.edit_instrument(instrument.id)

        controller.remove_voice(instrument.id)

        assert editor.edited_instrument() is None


class TestWritingIntoTheInstrument:
    def test_an_envelope_reaches_the_instrument(
        self,
        editor: InstrumentEditor,
        controller: ProjectController,
    ) -> None:
        instrument = controller.add_instrument(new_instrument("lead"))
        editor.edit_instrument(instrument.id)

        editor.write_envelope(FeatureKey.VOLUME, Envelope(items=VOLUME))

        assert instrument.envelopes.volume.items == VOLUME

    def test_a_point_written_on_an_envelope_reaches_the_instrument(
        self,
        editor: InstrumentEditor,
        controller: ProjectController,
    ) -> None:
        """A dimension carries the item it repeats from, so an edit writes both at once."""
        instrument = controller.add_instrument(new_instrument("lead"))
        editor.edit_instrument(instrument.id)

        editor.write_envelope(FeatureKey.VOLUME, Envelope(items=(15, 8), loop_point=0))

        assert instrument.envelopes.volume.items == (15, 8)
        assert instrument.envelopes.volume.loop_point == 0

    def test_a_write_with_no_instrument_in_front_is_refused(self, editor: InstrumentEditor) -> None:
        with pytest.raises(TypeError):
            editor.write_envelope(FeatureKey.VOLUME, Envelope(items=VOLUME))
