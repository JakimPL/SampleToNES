from typing import Callable, Dict, FrozenSet, Optional

import numpy as np

from sampletones_application.layout.behavior.scheduling.scheduling import (
    SchedulingBehavior,
)
from sampletones_application.logic.reconstruction.manager import ReconstructionManager
from sampletones_application.utils.callbacks.queue import CallbackQueue
from sampletones_application.view_model.reconstruction.instruments import (
    ReconstructionInstrumentsViewModel,
)
from sampletones_application.view_model.reconstruction.update import (
    ReconstructionUpdate,
)
from sampletones_application.view_model.shared.footprint import SampleFootprintViewModel
from sampletones_core.constants.enums import FeatureKey, GeneratorName
from sampletones_core.exporters import Features
from sampletones_core.formats.famitracker.footprint import features_footprint
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
        generators = self._current_generators()
        self.call(self.on_view_changed, self._build_view_model(generators))
        self.call(self.on_feature_data_changed, generators)

    def refresh_footprint(self) -> None:
        """Reports the sizes the loaded envelopes occupy, leaving the displayed envelopes as they are.

        A regeneration replaces what an instrument exports, so the byte figures settle on it. The
        envelopes themselves are left to the edit that started the regeneration, so a field the
        user is still typing in keeps what they wrote.
        """
        self.call(self.on_view_changed, self._build_view_model(self._current_generators()))

    def _current_generators(self) -> Optional[Dict[GeneratorName, Features]]:
        feature_data = self.reconstruction_manager.current_features
        return None if feature_data is None else feature_data.generators

    def _build_view_model(
        self,
        generators: Optional[Dict[GeneratorName, Features]],
    ) -> ReconstructionInstrumentsViewModel:
        if generators is None:
            return ReconstructionInstrumentsViewModel(
                reconstruction_loaded=False,
                available_generators=frozenset(),
                footprint=None,
            )

        available_generators: FrozenSet[GeneratorName] = frozenset(generators.keys())
        return ReconstructionInstrumentsViewModel(
            reconstruction_loaded=True,
            available_generators=available_generators,
            footprint=self._build_footprint(generators),
        )

    def _build_footprint(
        self,
        generators: Dict[GeneratorName, Features],
    ) -> SampleFootprintViewModel:
        """Measures each channel's instrument as the size its own export writes.

        A reconstruction has no loop flag of its own — that belongs to a sample placed in a
        project — so each instrument is measured playing its envelopes once, matching what
        **Export instrument...** produces.
        """
        return SampleFootprintViewModel.from_footprints(
            {
                generator_name: features_footprint(features, loop=False)
                for generator_name, features in generators.items()
            }
        )

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
        self._report_edited_size(generator_name, feature_key, data)
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
        self._report_edited_size(generator_name, feature_key, data)
        self._schedule_reconstruction_update(
            ReconstructionUpdate(
                generator_name,
                feature_key,
                data,
            )
        )

    def _report_edited_size(
        self,
        generator_name: GeneratorName,
        feature_key: FeatureKey,
        data: np.ndarray,
    ) -> None:
        """Reports what the edited envelope costs as the edit arrives, ahead of its regeneration.

        Measuring the envelope the user just wrote keeps the figures answering what is on screen
        while the reconstruction is still being rebuilt. The regenerated instruments report again
        once they land, so the figures settle on the exported form.
        """
        generators = self._current_generators()
        if generators is None:
            return

        self.call(
            self.on_view_changed,
            self._build_view_model(
                self._with_edit(
                    generators,
                    generator_name,
                    feature_key,
                    data,
                )
            ),
        )

    def _with_edit(
        self,
        generators: Dict[GeneratorName, Features],
        generator_name: GeneratorName,
        feature_key: FeatureKey,
        data: np.ndarray,
    ) -> Dict[GeneratorName, Features]:
        """The loaded channels with one envelope replaced, leaving the loaded ones as they are."""
        edited = generators[generator_name].model_copy(deep=True)
        edited[feature_key] = data
        return {**generators, generator_name: edited}

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
