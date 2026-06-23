from __future__ import annotations

from typing import Callable, Optional
from unittest.mock import MagicMock

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
        pitch_change_delay=0.1,
    )


class TestReconstructionDetailsLogicUpdateDisplay:
    def test_no_features_emits_not_loaded_view_model(
        self,
        details_logic: ReconstructionDetailsLogic,
        mock_reconstruction_manager: MagicMock,
    ) -> None:
        mock_reconstruction_manager.current_features = None
        received: list[Optional[ReconstructionDetailsViewModel]] = []
        details_logic.on_view_changed = received.append
        details_logic.update_display()
        assert len(received) == 1
        assert received[0].reconstruction_loaded is False

    def test_no_features_clears_current_pitches(
        self,
        details_logic: ReconstructionDetailsLogic,
        mock_reconstruction_manager: MagicMock,
    ) -> None:
        mock_reconstruction_manager.current_features = None
        details_logic._current_pitches[GeneratorName.PULSE1] = 60
        details_logic.update_display()
        assert details_logic._current_pitches == {}

    def test_no_features_fires_on_feature_data_changed_with_none(
        self,
        details_logic: ReconstructionDetailsLogic,
        mock_reconstruction_manager: MagicMock,
    ) -> None:
        mock_reconstruction_manager.current_features = None
        received: list = []
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
        received: list = []
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
        received: list = []
        details_logic.on_feature_data_changed = received.append
        details_logic.update_display()
        assert received == [feature_data]

    def test_with_features_populates_current_pitches(
        self,
        details_logic: ReconstructionDetailsLogic,
        mock_reconstruction_manager: MagicMock,
        reconstruction_factory: Callable[[], Reconstruction],
    ) -> None:
        mock_reconstruction_manager.current_features = FeatureData.load(reconstruction_factory())
        details_logic.update_display()
        assert GeneratorName.PULSE1 in details_logic._current_pitches


class TestReconstructionDetailsLogicHandlePitchInput:
    def test_numeric_text_is_parsed_as_int(
        self,
        details_logic: ReconstructionDetailsLogic,
        mock_reconstruction_manager: MagicMock,
    ) -> None:
        details_logic.handle_pitch_input(GeneratorName.PULSE1, "60", 50)
        assert details_logic._current_pitches[GeneratorName.PULSE1] == 60

    def test_note_name_resolves_to_pitch(
        self,
        details_logic: ReconstructionDetailsLogic,
        mock_reconstruction_manager: MagicMock,
    ) -> None:
        details_logic.handle_pitch_input(GeneratorName.PULSE1, "C-3", 50)
        assert details_logic._current_pitches[GeneratorName.PULSE1] == 60

    def test_invalid_text_falls_back_to_current_raw_value(
        self,
        details_logic: ReconstructionDetailsLogic,
        mock_reconstruction_manager: MagicMock,
    ) -> None:
        details_logic.handle_pitch_input(GeneratorName.PULSE1, "not_a_note", 55)
        assert details_logic._current_pitches[GeneratorName.PULSE1] == 55

    def test_noise_generator_clamps_as_period(
        self,
        details_logic: ReconstructionDetailsLogic,
        mock_reconstruction_manager: MagicMock,
    ) -> None:
        from sampletones_core.utils.frequencies import MAX_PERIOD

        details_logic.handle_pitch_input(GeneratorName.NOISE, "9999", 0)
        assert details_logic._current_pitches[GeneratorName.NOISE] <= MAX_PERIOD

    def test_noise_hex_name_resolves_to_period(
        self,
        details_logic: ReconstructionDetailsLogic,
        mock_reconstruction_manager: MagicMock,
    ) -> None:
        details_logic.handle_pitch_input(GeneratorName.NOISE, "A-#", 0)
        assert details_logic._current_pitches[GeneratorName.NOISE] == 10

    def test_noise_invalid_name_falls_back_to_current_raw_value(
        self,
        details_logic: ReconstructionDetailsLogic,
        mock_reconstruction_manager: MagicMock,
    ) -> None:
        details_logic.handle_pitch_input(GeneratorName.NOISE, "not_a_period", 3)
        assert details_logic._current_pitches[GeneratorName.NOISE] == 3

    def test_fires_on_pitch_changed_callback(
        self,
        details_logic: ReconstructionDetailsLogic,
        mock_reconstruction_manager: MagicMock,
    ) -> None:
        callback = MagicMock()
        details_logic.on_pitch_changed = callback
        details_logic.handle_pitch_input(GeneratorName.PULSE1, "60", 50)
        callback.assert_called_once_with(GeneratorName.PULSE1, 60)

    def test_schedules_reconstruction_update(
        self,
        details_logic: ReconstructionDetailsLogic,
        mock_reconstruction_manager: MagicMock,
    ) -> None:
        callback = MagicMock()
        details_logic.on_reconstruction_instrument_updated = callback
        details_logic.handle_pitch_input(GeneratorName.PULSE1, "60", 50)
        callback.assert_called_once()


class TestReconstructionDetailsLogicHandleHoldTick:
    def test_hold_tick_with_no_direction_is_no_op(
        self,
        details_logic: ReconstructionDetailsLogic,
    ) -> None:
        callback = MagicMock()
        details_logic.on_pitch_changed = callback
        details_logic.handle_hold_tick(False, False, 0.05, GeneratorName.PULSE1)
        callback.assert_not_called()

    def test_hold_tick_after_timer_fires_calls_pitch_step(
        self,
        details_logic: ReconstructionDetailsLogic,
    ) -> None:
        details_logic._current_pitches[GeneratorName.PULSE1] = 60
        details_logic._update_hold_timer(False, True, 0.0)
        details_logic._hold_timer = 0.0
        callback = MagicMock()
        details_logic.on_pitch_changed = callback
        details_logic.handle_hold_tick(False, True, 0.01, GeneratorName.PULSE1)
        callback.assert_called_once()


class TestReconstructionDetailsLogicHandleBarPoint:
    def test_handle_bar_point_clicked_schedules_update(
        self,
        details_logic: ReconstructionDetailsLogic,
        mock_reconstruction_manager: MagicMock,
    ) -> None:
        import numpy as np

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
        import numpy as np

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


class TestReconstructionDetailsLogicHandlePitchStep:
    def test_step_increments_pitch(
        self,
        details_logic: ReconstructionDetailsLogic,
        mock_reconstruction_manager: MagicMock,
    ) -> None:
        details_logic._current_pitches[GeneratorName.PULSE1] = 60
        details_logic.handle_pitch_step(GeneratorName.PULSE1, 1)
        assert details_logic._current_pitches[GeneratorName.PULSE1] == 61

    def test_step_decrements_pitch(
        self,
        details_logic: ReconstructionDetailsLogic,
        mock_reconstruction_manager: MagicMock,
    ) -> None:
        details_logic._current_pitches[GeneratorName.PULSE1] = 60
        details_logic.handle_pitch_step(GeneratorName.PULSE1, -1)
        assert details_logic._current_pitches[GeneratorName.PULSE1] == 59

    def test_noise_generator_uses_period_clamping(
        self,
        details_logic: ReconstructionDetailsLogic,
        mock_reconstruction_manager: MagicMock,
    ) -> None:
        from sampletones_core.utils.frequencies import MAX_PERIOD

        details_logic._current_pitches[GeneratorName.NOISE] = MAX_PERIOD
        details_logic.handle_pitch_step(GeneratorName.NOISE, 1)
        assert details_logic._current_pitches[GeneratorName.NOISE] == MAX_PERIOD

    def test_no_current_pitch_is_a_no_op(
        self,
        details_logic: ReconstructionDetailsLogic,
    ) -> None:
        callback = MagicMock()
        details_logic.on_pitch_changed = callback
        details_logic.handle_pitch_step(GeneratorName.PULSE1, 1)
        callback.assert_not_called()


class TestReconstructionDetailsLogicHoldTimer:
    def test_first_call_sets_timer_and_returns_none(
        self,
        details_logic: ReconstructionDetailsLogic,
    ) -> None:
        result = details_logic._update_hold_timer(True, False, 0.05)
        assert result is None
        assert details_logic._hold_timer is not None

    def test_same_direction_before_timer_expires_returns_none(
        self,
        details_logic: ReconstructionDetailsLogic,
    ) -> None:
        details_logic._update_hold_timer(True, False, 0.0)
        result = details_logic._update_hold_timer(True, False, 0.05)
        assert result is None

    def test_same_direction_after_timer_expires_returns_direction(
        self,
        details_logic: ReconstructionDetailsLogic,
    ) -> None:
        details_logic._update_hold_timer(False, True, 0.0)
        details_logic._hold_timer = 0.0
        result = details_logic._update_hold_timer(False, True, 0.01)
        assert result == 1

    def test_direction_change_resets_timer(
        self,
        details_logic: ReconstructionDetailsLogic,
    ) -> None:
        details_logic._update_hold_timer(True, False, 0.0)
        old_timer = details_logic._hold_timer
        details_logic._update_hold_timer(False, True, 0.0)
        assert details_logic._hold_timer == old_timer

    def test_handle_hold_ended_clears_timer_and_direction(
        self,
        details_logic: ReconstructionDetailsLogic,
    ) -> None:
        details_logic._update_hold_timer(True, False, 0.0)
        details_logic.handle_hold_ended()
        assert details_logic._hold_timer is None
        assert details_logic._hold_direction is None

    def test_neither_pressed_returns_none(
        self,
        details_logic: ReconstructionDetailsLogic,
    ) -> None:
        result = details_logic._update_hold_timer(False, False, 0.05)
        assert result is None
