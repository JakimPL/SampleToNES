from typing import Final, Tuple
from unittest.mock import MagicMock

import numpy as np
import pytest

from sampletones_application.logic.project.controller import ProjectController
from sampletones_application.logic.project.manager import ProjectManager
from sampletones_application.logic.reconstruction.editing import ReconstructionEdit, ShapeEdit
from sampletones_application.logic.reconstruction.editor import InstrumentEditor
from sampletones_application.logic.reconstruction.manager import ReconstructionManager
from sampletones_core.constants.enums import ChannelName, FeatureKey
from sampletones_core.exporters import Features
from sampletones_core.project.voices.loop import WHOLE_LOOP_POINT

ROOT_PITCH: Final[int] = 55
ROOT_PERIOD: Final[int] = 3
VOLUME: Final[Tuple[int, ...]] = (15, 12, 9)


def _features() -> Features:
    return Features(
        initial_pitch=ROOT_PITCH,
        volume=np.array([15], dtype=np.int8),
        arpeggio=np.array([0], dtype=np.int8),
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


@pytest.fixture
def editor(reconstruction_manager: MagicMock, controller: ProjectController) -> InstrumentEditor:
    return InstrumentEditor(reconstruction_manager, controller)


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

    def test_a_shape_answers_with_what_it_states(
        self,
        editor: InstrumentEditor,
        controller: ProjectController,
    ) -> None:
        shape = controller.add_shape("lead")
        controller.set_shape_root(shape.id, pitch=ROOT_PITCH, period=ROOT_PERIOD)

        editor.edit_shape(shape.id)

        edit = editor.edited_instrument()
        assert isinstance(edit, ShapeEdit)
        assert (edit.voice_id, edit.name) == (shape.id, "lead")
        assert (edit.root_pitch, edit.root_period) == (ROOT_PITCH, ROOT_PERIOD)

    def test_opening_a_shape_closes_the_reconstruction_the_tab_held(
        self,
        editor: InstrumentEditor,
        controller: ProjectController,
        reconstruction_manager: MagicMock,
    ) -> None:
        """The tab describes one voice, so its waveform and stems follow what is in front of it."""
        shape = controller.add_shape("lead")

        editor.edit_shape(shape.id)

        reconstruction_manager.close_reconstruction.assert_called_once_with()

    def test_letting_go_of_a_shape_hands_the_tab_back(
        self,
        editor: InstrumentEditor,
        controller: ProjectController,
        reconstruction_manager: MagicMock,
    ) -> None:
        shape = controller.add_shape("lead")
        editor.edit_shape(shape.id)
        reconstruction_manager.current_features = MagicMock(channels={ChannelName.PULSE1: _features()})

        editor.release_shape()

        assert isinstance(editor.edited_instrument(), ReconstructionEdit)

    def test_a_shape_removed_from_the_project_leaves_the_tab_holding_nothing(
        self,
        editor: InstrumentEditor,
        controller: ProjectController,
    ) -> None:
        shape = controller.add_shape("lead")
        editor.edit_shape(shape.id)

        controller.remove_voice(shape.id)

        assert editor.edited_instrument() is None


class TestWritingIntoTheShape:
    def test_an_envelope_reaches_the_shape(
        self,
        editor: InstrumentEditor,
        controller: ProjectController,
    ) -> None:
        shape = controller.add_shape("lead")
        editor.edit_shape(shape.id)

        editor.write_envelope(FeatureKey.VOLUME, np.array(VOLUME, dtype=np.int8))

        assert shape.envelopes.volume == VOLUME

    def test_the_roots_reach_the_shape(
        self,
        editor: InstrumentEditor,
        controller: ProjectController,
    ) -> None:
        shape = controller.add_shape("lead")
        editor.edit_shape(shape.id)

        editor.write_roots(pitch=ROOT_PITCH, period=ROOT_PERIOD)

        assert (shape.root_pitch, shape.root_period) == (ROOT_PITCH, ROOT_PERIOD)

    def test_the_loop_point_reaches_the_shape(
        self,
        editor: InstrumentEditor,
        controller: ProjectController,
    ) -> None:
        shape = controller.add_shape("lead")
        editor.edit_shape(shape.id)

        editor.write_loop_point(WHOLE_LOOP_POINT)

        assert shape.loop_point == WHOLE_LOOP_POINT

    def test_a_write_with_no_shape_in_front_is_refused(self, editor: InstrumentEditor) -> None:
        with pytest.raises(TypeError):
            editor.write_envelope(FeatureKey.VOLUME, np.array(VOLUME, dtype=np.int8))
