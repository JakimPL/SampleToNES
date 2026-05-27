from typing import Callable, Dict, FrozenSet, Optional, cast

import numpy as np

from sampletones_application.constants.general import (
    VAL_DELAY_SCHEDULE,
    VAL_PRIORITY_SCHEDULE,
)
from sampletones_application.constants.reconstructions import VAL_DELAY_RECONSTRUCTIONS_DETAILS_INITIAL_PITCH_CHANGE
from sampletones_application.logic.reconstruction.feature import FeatureData
from sampletones_application.logic.reconstruction.manager import ReconstructionManager
from sampletones_application.logic.reconstruction.update import ReconstructionUpdate
from sampletones_application.utils.callbacks.queue import CallbackQueue
from sampletones_application.view_model.reconstruction.details import ReconstructionDetailsViewModel
from sampletones_core.constants.enums import FeatureKey, GeneratorName
from sampletones_core.exporters import Features
from sampletones_core.types.feature import FeatureValue
from sampletones_core.utils.frequencies import (
    SANITIZED_NAME_TO_PERIOD,
    SANITIZED_NAME_TO_PITCH,
    clamp_period,
    clamp_pitch,
    sanitize_period,
    sanitize_pitch,
)
from sampletones_shared.utils.callbacks import CallbackMixin

OnReconstructionInstrumentUpdatedCallback = Callable[[GeneratorName, Features, FeatureKey, FeatureValue], None]


class ReconstructionDetailsLogic(CallbackMixin):
    def __init__(self, reconstruction_manager: ReconstructionManager) -> None:
        self.reconstruction_manager = reconstruction_manager

        self._pending_reconstruction_update: Optional[ReconstructionUpdate] = None
        self._hold_direction: Optional[int] = None
        self._hold_timer: Optional[float] = None
        self._current_pitches: Dict[GeneratorName, int] = {}

        self.on_view_changed: Optional[Callable[[ReconstructionDetailsViewModel], None]] = None
        self.on_feature_data_changed: Optional[Callable[[Optional[FeatureData]], None]] = None
        self.on_pitch_changed: Optional[Callable[[GeneratorName, int], None]] = None
        self.on_reconstruction_instrument_updated: Optional[OnReconstructionInstrumentUpdatedCallback] = None

    def update_display(self) -> None:
        feature_data = self.reconstruction_manager._current_features
        if feature_data is None:
            self._current_pitches = {}
            self.call(
                self.on_view_changed,
                ReconstructionDetailsViewModel(
                    reconstruction_loaded=False,
                    available_generators=frozenset(),
                    buttons_enabled=False,
                ),
            )
            self.call(self.on_feature_data_changed, None)
            return

        available_generators: FrozenSet[GeneratorName] = frozenset(feature_data.generators.keys())

        for generator_name in GeneratorName.items():
            if generator_name not in available_generators:
                continue

            generator_features = feature_data.get_generator_features(generator_name)
            if generator_features is not None:
                self._current_pitches[generator_name] = cast(int, generator_features[FeatureKey.INITIAL_PITCH])

        self.call(
            self.on_view_changed,
            ReconstructionDetailsViewModel(
                reconstruction_loaded=True,
                available_generators=available_generators,
                buttons_enabled=True,
            ),
        )
        self.call(self.on_feature_data_changed, feature_data)

    def handle_pitch_input(self, generator_name: GeneratorName, text: str, current_raw_value: int) -> None:
        new_pitch = self._parse_pitch_text(generator_name, text, current_raw_value)
        self._current_pitches[generator_name] = new_pitch
        self.call(self.on_pitch_changed, generator_name, new_pitch)
        self._schedule_reconstruction_update(
            ReconstructionUpdate(
                generator_name,
                FeatureKey.INITIAL_PITCH,
                new_pitch,
            )
        )

    def handle_pitch_step(self, generator_name: GeneratorName, direction: int) -> None:
        current = self._current_pitches.get(generator_name)
        if current is None:
            return

        if generator_name == GeneratorName.NOISE:
            new_pitch = clamp_period(current + direction)
        else:
            new_pitch = clamp_pitch(current + direction)

        self._current_pitches[generator_name] = new_pitch
        self.call(self.on_pitch_changed, generator_name, new_pitch)
        self._schedule_reconstruction_update(
            ReconstructionUpdate(
                generator_name,
                FeatureKey.INITIAL_PITCH,
                new_pitch,
            )
        )

    def handle_hold_tick(
        self,
        is_decrement: bool,
        is_increment: bool,
        delta_time: float,
        generator_name: GeneratorName,
    ) -> None:
        direction = self._update_hold_timer(is_decrement, is_increment, delta_time)
        if direction is not None:
            self.handle_pitch_step(generator_name, direction)

    def handle_hold_ended(self) -> None:
        self._hold_timer = None
        self._hold_direction = None

    def handle_bar_point_clicked(
        self,
        generator_name: GeneratorName,
        feature_key: FeatureKey,
        data: np.ndarray,
    ) -> None:
        self._schedule_reconstruction_update(
            ReconstructionUpdate(
                generator_name,
                feature_key,
                data,
            )
        )

    def handle_raw_data_changed(
        self,
        generator_name: GeneratorName,
        feature_key: FeatureKey,
        data: np.ndarray,
    ) -> None:
        self._schedule_reconstruction_update(
            ReconstructionUpdate(
                generator_name,
                feature_key,
                data,
            )
        )

    def _update_hold_timer(self, is_decrement: bool, is_increment: bool, delta_time: float) -> Optional[int]:
        if not is_decrement and not is_increment:
            return None

        direction = -1 if is_decrement else 1
        if self._hold_direction != direction or self._hold_timer is None:
            self._hold_direction = direction
            self._hold_timer = 3 * VAL_DELAY_RECONSTRUCTIONS_DETAILS_INITIAL_PITCH_CHANGE
            return None

        self._hold_timer -= delta_time
        if self._hold_timer > 0:
            return None

        self._hold_timer = VAL_DELAY_RECONSTRUCTIONS_DETAILS_INITIAL_PITCH_CHANGE
        return direction

    def _parse_pitch_text(self, generator_name: GeneratorName, text: str, current_raw_value: int) -> int:
        try:
            value = int(text)
            if generator_name == GeneratorName.NOISE:
                return clamp_period(value)

            return clamp_pitch(value)
        except ValueError:
            name = text.strip()
            if generator_name == GeneratorName.NOISE:
                name = sanitize_period(name)
                if name not in SANITIZED_NAME_TO_PERIOD:
                    return current_raw_value
                return SANITIZED_NAME_TO_PERIOD[name]

            name = sanitize_pitch(name)
            if name not in SANITIZED_NAME_TO_PITCH:
                return current_raw_value

            return SANITIZED_NAME_TO_PITCH[name]

    def _schedule_reconstruction_update(self, update: ReconstructionUpdate) -> None:
        self._pending_reconstruction_update = update
        CallbackQueue.add(
            self._on_reconstruction_update_scheduled,
            priority=VAL_PRIORITY_SCHEDULE,
            delay=VAL_DELAY_SCHEDULE,
        )

    def _on_reconstruction_update_scheduled(self) -> None:
        if self._pending_reconstruction_update is None:
            return

        generator_name, feature_key, data = self._pending_reconstruction_update
        self._pending_reconstruction_update = None
        self.call(
            self.on_reconstruction_instrument_updated,
            generator_name,
            self._get_features(generator_name),
            feature_key,
            data,
        )

    def _get_features(self, generator_name: GeneratorName) -> Features:
        current_features = self.reconstruction_manager._current_features
        assert current_features is not None, "Current features should not be None"

        features = current_features.get_generator_features(generator_name)
        assert features is not None, f"Features for generator {generator_name} should not be None"
        return features
