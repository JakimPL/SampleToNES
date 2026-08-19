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
from sampletones_core.constants.enums import ChannelName, FeatureKey
from sampletones_core.exporters import Features
from sampletones_core.formats.famitracker.footprint import features_footprint
from sampletones_core.types.feature import FeatureValue
from sampletones_shared.utils.callbacks import CallbackMixin

OnReconstructionInstrumentUpdatedCallback = Callable[
    [ChannelName, Features, FeatureKey, FeatureValue],
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
        self.on_feature_data_changed: Optional[Callable[[Optional[Dict[ChannelName, Features]]], None]] = None
        self.on_reconstruction_instrument_updated: Optional[OnReconstructionInstrumentUpdatedCallback] = None

    def update_display(self) -> None:
        channels = self._current_generators()
        self.call(self.on_view_changed, self._build_view_model(channels))
        self.call(self.on_feature_data_changed, channels)

    def refresh_view(self) -> None:
        """Reports which channels play and the sizes they occupy, leaving the displayed envelopes as they are.

        A regeneration replaces what an instrument exports, so the byte figures and the standing-by
        channels settle on it. The envelopes themselves are left to the edit that started the
        regeneration, so a field the user is still typing in keeps what they wrote.
        """
        self.call(self.on_view_changed, self._build_view_model(self._current_generators()))

    def _current_generators(self) -> Optional[Dict[ChannelName, Features]]:
        feature_data = self.reconstruction_manager.current_features
        return None if feature_data is None else feature_data.channels

    def _build_view_model(
        self,
        channels: Optional[Dict[ChannelName, Features]],
    ) -> ReconstructionInstrumentsViewModel:
        if channels is None:
            return ReconstructionInstrumentsViewModel(
                reconstruction_loaded=False,
                playing_channels=frozenset(),
                footprint=None,
            )

        playing_channels: FrozenSet[ChannelName] = frozenset(
            channel_name for channel_name, features in channels.items() if features.has_frames
        )
        return ReconstructionInstrumentsViewModel(
            reconstruction_loaded=True,
            playing_channels=playing_channels,
            footprint=self._build_footprint(channels),
        )

    def _build_footprint(
        self,
        channels: Dict[ChannelName, Features],
    ) -> SampleFootprintViewModel:
        """Measures each playing channel's instrument as the size its own export writes.

        A reconstruction has no loop flag of its own — that belongs to a sample placed in a
        project — so each instrument is measured playing its envelopes once, matching what
        **Export instrument...** produces. A channel standing by is written nowhere, so it is
        measured nowhere and the sample's total names what the export costs.
        """
        return SampleFootprintViewModel.from_footprints(
            {
                channel_name: features_footprint(features, loop=False)
                for channel_name, features in channels.items()
                if features.has_frames
            }
        )

    def handle_pitch_value_changed(
        self,
        channel_name: ChannelName,
        value: int,
    ) -> None:
        self._schedule_reconstruction_update(
            ReconstructionUpdate(
                channel_name,
                FeatureKey.INITIAL_PITCH,
                value,
            )
        )

    def handle_bar_point_clicked(
        self,
        channel_name: ChannelName,
        feature_key: FeatureKey,
        data: np.ndarray,
    ) -> None:
        self._report_edited_size(channel_name, feature_key, data)
        self._schedule_reconstruction_update(
            ReconstructionUpdate(
                channel_name,
                feature_key,
                data,
            )
        )

    def handle_raw_data_changed(
        self,
        channel_name: ChannelName,
        feature_key: FeatureKey,
        data: np.ndarray,
    ) -> None:
        self._report_edited_size(channel_name, feature_key, data)
        self._schedule_reconstruction_update(
            ReconstructionUpdate(
                channel_name,
                feature_key,
                data,
            )
        )

    def _report_edited_size(
        self,
        channel_name: ChannelName,
        feature_key: FeatureKey,
        data: np.ndarray,
    ) -> None:
        """Reports what the edited envelope costs as the edit arrives, ahead of its regeneration.

        Measuring the envelope the user just wrote keeps the figures answering what is on screen
        while the reconstruction is still being rebuilt. The regenerated instruments report again
        once they land, so the figures settle on the exported form.
        """
        channels = self._current_generators()
        if channels is None:
            return

        self.call(
            self.on_view_changed,
            self._build_view_model(
                self._with_edit(
                    channels,
                    channel_name,
                    feature_key,
                    data,
                )
            ),
        )

    def _with_edit(
        self,
        channels: Dict[ChannelName, Features],
        channel_name: ChannelName,
        feature_key: FeatureKey,
        data: np.ndarray,
    ) -> Dict[ChannelName, Features]:
        """The loaded channels with one envelope replaced, leaving the loaded ones as they are."""
        edited = channels[channel_name].model_copy(deep=True)
        edited[feature_key] = data
        return {**channels, channel_name: edited}

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

        channel_name, feature_key, data = self._pending_reconstruction_update
        self._pending_reconstruction_update = None
        self.call(
            self.on_reconstruction_instrument_updated,
            channel_name,
            self._get_features(channel_name),
            feature_key,
            data,
        )

    def _get_features(self, channel_name: ChannelName) -> Features:
        current_features = self.reconstruction_manager.current_features
        assert current_features is not None, "Current features should not be None"

        return current_features[channel_name]
