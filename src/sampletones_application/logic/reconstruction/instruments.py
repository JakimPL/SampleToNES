from typing import Callable, Dict, Optional

from sampletones_application.constants.instruments import INSTRUMENT_CHANNEL
from sampletones_application.layout.behavior.scheduling.scheduling import (
    SchedulingBehavior,
)
from sampletones_application.logic.reconstruction.editing import (
    InstrumentEdit,
    InstrumentEditingProtocol,
    ReconstructionEdit,
)
from sampletones_application.utils.callbacks.queue import CallbackQueue
from sampletones_application.view_model.reconstruction.instruments import (
    InstrumentViewModel,
    ReconstructionInstrumentsViewModel,
)
from sampletones_application.view_model.reconstruction.update import (
    ReconstructionUpdate,
)
from sampletones_application.view_model.shared.footprint import SampleFootprintViewModel
from sampletones_core.constants.enums import ChannelName, FeatureKey
from sampletones_core.exporters import Features, playing_channels
from sampletones_core.features.envelope import Envelope
from sampletones_core.formats.famitracker.footprint import features_footprint
from sampletones_shared.utils.callbacks import CallbackMixin

OnReconstructionInstrumentUpdatedCallback = Callable[
    [ChannelName, FeatureKey, Features],
    None,
]


class ReconstructionInstrumentsLogic(CallbackMixin):
    def __init__(
        self,
        editor: InstrumentEditingProtocol,
        *,
        scheduling: SchedulingBehavior,
    ) -> None:
        self._editor = editor
        self._scheduling = scheduling

        self._pending_reconstruction_update: Optional[ReconstructionUpdate] = None

        self.on_view_changed: Optional[Callable[[ReconstructionInstrumentsViewModel], None]] = None
        self.on_feature_data_changed: Optional[Callable[[Optional[Dict[ChannelName, Features]]], None]] = None
        self.on_reconstruction_instrument_updated: Optional[OnReconstructionInstrumentUpdatedCallback] = None

    def update_display(self) -> None:
        """Renders whatever the panel has in front of it, envelopes and figures together."""
        self.call(self.on_view_changed, self._build_view_model(self._current_generators()))
        self.call(self.on_feature_data_changed, self._displayed_features())

    def _displayed_features(self) -> Optional[Dict[ChannelName, Features]]:
        """The envelopes the panel draws: a reconstruction's channels, or an instrument's own set.

        An instrument is drawn on the tab the panel shows it under, which is the channel offering every
        dimension an instrument writes.
        """
        instrument = self.instrument_edit
        if instrument is not None:
            return self._instrument_channels(instrument)

        return self._current_generators()

    @staticmethod
    def _instrument_channels(
        instrument: InstrumentEdit,
    ) -> Dict[ChannelName, Features]:
        """An instrument's envelopes under the channel the panel shows it on."""
        return {INSTRUMENT_CHANNEL: instrument.features}

    def refresh_view(self) -> None:
        """Reports which channels play and the sizes they occupy, leaving the displayed envelopes as they are.

        A regeneration replaces what an instrument exports, so the byte figures and the standing-by
        channels settle on it. The envelopes themselves are left to the edit that started the
        regeneration, so a field the user is still typing in keeps what they wrote.
        """
        self.call(
            self.on_view_changed,
            self._build_view_model(self._current_generators()),
        )

    def _current_generators(self) -> Optional[Dict[ChannelName, Features]]:
        """The channels of the reconstruction in front of the panel, where one is."""
        match self._editor.edited_instrument():
            case ReconstructionEdit() as edit:
                return edit.channels
            case _:
                return None

    @property
    def instrument_edit(self) -> Optional[InstrumentEdit]:
        """The instrument in front of the panel, where one is."""
        match self._editor.edited_instrument():
            case InstrumentEdit() as edit:
                return edit
            case _:
                return None

    def _build_view_model(
        self,
        channels: Optional[Dict[ChannelName, Features]],
    ) -> ReconstructionInstrumentsViewModel:
        instrument = self.instrument_edit
        if instrument is not None:
            return self._instrument_view_model(instrument)

        if channels is None:
            return ReconstructionInstrumentsViewModel(
                reconstruction_loaded=False,
                playing_channels=frozenset(),
                footprint=None,
            )

        return ReconstructionInstrumentsViewModel(
            reconstruction_loaded=True,
            playing_channels=playing_channels(channels),
            footprint=self._build_footprint(channels),
        )

    def _instrument_view_model(
        self,
        instrument: InstrumentEdit,
    ) -> ReconstructionInstrumentsViewModel:
        """What the panel shows of an instrument: its envelopes, its roots and what it costs.

        An instrument is shown under one channel, and it plays there once its envelopes describe a
        frame, so it stands by the way a reconstruction's silent channel does until the reader
        writes one.
        """
        return ReconstructionInstrumentsViewModel(
            reconstruction_loaded=False,
            playing_channels=playing_channels(self._instrument_channels(instrument)),
            footprint=SampleFootprintViewModel.from_instrument(features_footprint(instrument.features)),
            instrument=InstrumentViewModel(name=instrument.name),
        )

    def _build_footprint(
        self,
        channels: Dict[ChannelName, Features],
    ) -> SampleFootprintViewModel:
        """Measures each playing channel's instrument as the size its own export writes.

        Each instrument is measured at the lengths its own envelopes state, matching what
        **Export instrument...** produces. A channel standing by is written nowhere, so it is
        measured nowhere and the sample's total names what the export costs.
        """
        return SampleFootprintViewModel.from_footprints(
            {
                channel_name: features_footprint(features)
                for channel_name, features in channels.items()
                if features.has_frames
            }
        )

    def handle_pitch_value_changed(
        self,
        channel_name: ChannelName,
        value: int,
    ) -> None:
        instrument = self.instrument_edit
        if instrument is not None:
            self._editor.write_roots(
                pitch=value,
                period=instrument.initial_period,
            )
            self.update_display()
            return

        features = self._get_features(channel_name)
        self._schedule_reconstruction_update(
            ReconstructionUpdate(
                channel_name,
                FeatureKey.INITIAL_PITCH,
                features.model_copy(update={"initial_pitch": value}),
            )
        )

    def handle_envelope_changed(
        self,
        channel_name: ChannelName,
        feature_key: FeatureKey,
        envelope: Envelope[int],
    ) -> None:
        """Takes one dimension as an edit leaves it, values and loop point together.

        The panel states the whole dimension, so a bar redrawn on the plot and a sequence typed
        into the text field arrive the same way and are written the same way.
        """
        if self._write_instrument_envelope(feature_key, envelope):
            return

        features = self._get_features(channel_name).with_envelope(feature_key, envelope)
        self._report_edited_size(channel_name, features)
        self._schedule_reconstruction_update(ReconstructionUpdate(channel_name, feature_key, features))

    def _write_instrument_envelope(
        self,
        feature_key: FeatureKey,
        envelope: Envelope[int],
    ) -> bool:
        """Writes one dimension of the instrument in front of the panel, reporting whether it did.

        An instrument stands on no audio, so an edit reaches it at once rather than through the
        regeneration a reconstruction's envelopes go back through.
        """
        if self.instrument_edit is None:
            return False

        self._editor.write_envelope(feature_key, envelope)
        self.update_display()
        return True

    def _report_edited_size(
        self,
        channel_name: ChannelName,
        features: Features,
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
            self._build_view_model({**channels, channel_name: features}),
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

        channel_name, feature_key, features = self._pending_reconstruction_update
        self._pending_reconstruction_update = None
        self.call(self.on_reconstruction_instrument_updated, channel_name, feature_key, features)

    def _get_features(self, channel_name: ChannelName) -> Features:
        channels = self._current_generators()
        assert channels is not None, "A channel edit arrives only while a reconstruction is open"

        return channels[channel_name]
