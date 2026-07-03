from __future__ import annotations

from typing import Callable, List, Optional
from unittest.mock import MagicMock

import numpy as np
import pytest

from sampletones_application.layout.behavior import SchedulingBehavior
from sampletones_application.logic.reconstruction.details import ReconstructionDetailsLogic
from sampletones_application.logic.reconstruction.feature import FeatureData
from sampletones_application.logic.reconstruction.manager import ReconstructionManager
from sampletones_application.view_model.reconstruction.details import ReconstructionDetailsViewModel
from sampletones_core.constants.enums import FeatureKey, GeneratorName
from sampletones_core.reconstructions import Reconstruction


@pytest.fixture
def mock_reconstruction_manager() -> MagicMock:
    return MagicMock(spec=ReconstructionManager)


@pytest.fixture
def details_logic(mock_reconstruction_manager: MagicMock, scheduling: SchedulingBehavior) -> ReconstructionDetailsLogic:
    return ReconstructionDetailsLogic(
        mock_reconstruction_manager,
        scheduling=scheduling,
    )


class TestReconstructionDetailsLogicUpdateDisplay:
    def test_no_features_emits_not_loaded_view_model(
        self,
        details_logic: ReconstructionDetailsLogic,
        mock_reconstruction_manager: MagicMock,
    ) -> None:
        mock_reconstruction_manager.current_features = None
        received: List[ReconstructionDetailsViewModel] = []
        details_logic.on_view_changed = received.append
        details_logic.update_display()
        assert len(received) == 1
        assert received[0].reconstruction_loaded is False

    def test_no_features_fires_on_feature_data_changed_with_none(
        self,
        details_logic: ReconstructionDetailsLogic,
        mock_reconstruction_manager: MagicMock,
    ) -> None:
        mock_reconstruction_manager.current_features = None
        received: List[Optional[FeatureData]] = []
        details_logic.on_feature_data_changed = received.append
        details_logic.update_display()
        assert received == [None]

    def test_with_features_emits_loaded_view_model(
        self,
        details_logic: ReconstructionDetailsLogic,
        mock_reconstruction_manager: MagicMock,
        reconstruction_factory: Callable[[], Reconstruction],
    ) -> None:
        mock_reconstruction_manager.current_features = FeatureData.load(reconstruction_factory())
        received: List[ReconstructionDetailsViewModel] = []
        details_logic.on_view_changed = received.append
        details_logic.update_display()
        assert received[0].reconstruction_loaded is True

    def test_with_features_fires_on_feature_data_changed_with_data(
        self,
        details_logic: ReconstructionDetailsLogic,
        mock_reconstruction_manager: MagicMock,
        reconstruction_factory: Callable[[], Reconstruction],
    ) -> None:
        feature_data = FeatureData.load(reconstruction_factory())
        mock_reconstruction_manager.current_features = feature_data
        received: List[Optional[FeatureData]] = []
        details_logic.on_feature_data_changed = received.append
        details_logic.update_display()
        assert received == [feature_data]

    def test_with_features_exposes_available_generators(
        self,
        details_logic: ReconstructionDetailsLogic,
        mock_reconstruction_manager: MagicMock,
        reconstruction_factory: Callable[[], Reconstruction],
    ) -> None:
        mock_reconstruction_manager.current_features = FeatureData.load(reconstruction_factory())
        received: List[ReconstructionDetailsViewModel] = []
        details_logic.on_view_changed = received.append
        details_logic.update_display()
        assert GeneratorName.PULSE1 in received[0].available_generators


class TestReconstructionDetailsLogicHandlePitchValueChanged:
    def test_schedules_reconstruction_update(
        self,
        details_logic: ReconstructionDetailsLogic,
        mock_reconstruction_manager: MagicMock,
    ) -> None:
        callback = MagicMock()
        details_logic.on_reconstruction_instrument_updated = callback
        details_logic.handle_pitch_value_changed(GeneratorName.PULSE1, 61)
        callback.assert_called_once()

    def test_forwards_generator_pitch_feature_and_value(
        self,
        details_logic: ReconstructionDetailsLogic,
        mock_reconstruction_manager: MagicMock,
    ) -> None:
        callback = MagicMock()
        details_logic.on_reconstruction_instrument_updated = callback
        details_logic.handle_pitch_value_changed(GeneratorName.PULSE1, 61)
        generator_name, _features, feature_key, value = callback.call_args.args
        assert generator_name == GeneratorName.PULSE1
        assert feature_key == FeatureKey.INITIAL_PITCH
        assert value == 61


class TestReconstructionDetailsLogicHandleBarPoint:
    def test_handle_bar_point_clicked_schedules_update(
        self,
        details_logic: ReconstructionDetailsLogic,
        mock_reconstruction_manager: MagicMock,
    ) -> None:
        callback = MagicMock()
        details_logic.on_reconstruction_instrument_updated = callback
        details_logic.handle_bar_point_clicked(
            GeneratorName.PULSE1,
            FeatureKey.VOLUME,
            np.zeros(4, dtype=np.float32),
        )
        callback.assert_called_once()


class TestReconstructionDetailsLogicHandleRawData:
    def test_handle_raw_data_changed_schedules_update(
        self,
        details_logic: ReconstructionDetailsLogic,
        mock_reconstruction_manager: MagicMock,
    ) -> None:
        callback = MagicMock()
        details_logic.on_reconstruction_instrument_updated = callback
        details_logic.handle_raw_data_changed(
            GeneratorName.PULSE1,
            FeatureKey.ARPEGGIO,
            np.zeros(4, dtype=np.float32),
        )
        callback.assert_called_once()


class TestReconstructionDetailsLogicOnUpdateScheduled:
    def test_no_pending_update_is_a_no_op(
        self,
        details_logic: ReconstructionDetailsLogic,
    ) -> None:
        callback = MagicMock()
        details_logic.on_reconstruction_instrument_updated = callback
        details_logic._pending_reconstruction_update = None
        details_logic._on_reconstruction_update_scheduled()
        callback.assert_not_called()
