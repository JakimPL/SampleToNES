from typing import Callable, Dict, FrozenSet, Optional

import numpy as np

from sampletones_application.layout.behavior.scheduling.scheduling import SchedulingBehavior
from sampletones_application.logic.reconstruction.manager import ReconstructionManager
from sampletones_application.utils.callbacks.queue import CallbackQueue
from sampletones_application.view_model.reconstruction.instruments import (
    ReconstructionInstrumentsViewModel,
)
from sampletones_application.view_model.reconstruction.update import (
    ReconstructionUpdate,
)
from sampletones_core.constants.enums import FeatureKey, GeneratorName
from sampletones_core.exporters import Features
from sampletones_core.types.feature import FeatureValue
from sampletones_shared.utils.callbacks import CallbackMixin

OnReconstructionInstrumentUpdatedCallback = Callable[
    [GeneratorName, Features, FeatureKey, FeatureValue],
    None,
]


class ReconstructionInstrumentsLogic(CallbackMixin):
    def __init__(
        self,
        reconstruction_manager: ReconstructionManager,
        *,
        scheduling: SchedulingBehavior,
    ) -> None:
        self.reconstruction_manager = reconstruction_manager
        self._scheduling = scheduling

        self._pending_reconstruction_update: Optional[ReconstructionUpdate] = None

        self.on_view_changed: Optional[Callable[[ReconstructionInstrumentsViewModel], None]] = None
        self.on_feature_data_changed: Optional[Callable[[Optional[Dict[GeneratorName, Features]]], None]] = None
        self.on_reconstruction_instrument_updated: Optional[OnReconstructionInstrumentUpdatedCallback] = None

    def update_display(self) -> None:
        feature_data = self.reconstruction_manager.current_features
        if feature_data is None:
            self.call(
                self.on_view_changed,
                ReconstructionInstrumentsViewModel(
                    reconstruction_loaded=False,
                    available_generators=frozenset(),
                ),
            )
            self.call(self.on_feature_data_changed, None)
            return

        available_generators: FrozenSet[GeneratorName] = frozenset(feature_data.generators.keys())
        self.call(
            self.on_view_changed,
            ReconstructionInstrumentsViewModel(
                reconstruction_loaded=True,
                available_generators=available_generators,
            ),
        )
        self.call(self.on_feature_data_changed, feature_data.generators)

    def handle_pitch_value_changed(
        self,
        generator_name: GeneratorName,
        value: int,
    ) -> None:
        self._schedule_reconstruction_update(
            ReconstructionUpdate(
                generator_name,
                FeatureKey.INITIAL_PITCH,
                value,
            )
        )

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

    def _schedule_reconstruction_update(
        self,
        update: ReconstructionUpdate,
    ) -> None:
        """Coalesces a burst of edits into the latest pending update, then hands it off promptly.

        The slot keeps only the newest update so events arriving within the short debounce
        collapse into one. A dedicated, brief delay keeps the hand-off responsive; the
        regeneration service then applies last-wins across whatever it receives, so the final
        edit of a continuous drag is always applied.
        """
        self._pending_reconstruction_update = update
        CallbackQueue.add(
            self._on_reconstruction_update_scheduled,
            priority=self._scheduling.priorities.schedule,
            delay=self._scheduling.delays.reconstruction_update,
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
        current_features = self.reconstruction_manager.current_features
        assert current_features is not None, "Current features should not be None"

        features = current_features.get_generator_features(generator_name)
        assert features is not None, f"Features for generator {generator_name} should not be None"
        return features
