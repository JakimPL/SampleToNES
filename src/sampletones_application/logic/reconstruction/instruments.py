from typing import Callable, Dict, Optional, Protocol, Set

from sampletones_application.constants.instruments import INSTRUMENT_CHANNEL
from sampletones_application.logic.reconstruction.editing import (
    InstrumentEdit,
    InstrumentEditingProtocol,
)
from sampletones_application.logic.reconstruction.rewrites.steps import ChannelChange
from sampletones_application.view_model.reconstruction.envelopes import (
    ChannelEnvelopesViewModel,
)
from sampletones_application.view_model.reconstruction.instruments import (
    InstrumentViewModel,
    ReconstructionInstrumentsViewModel,
)
from sampletones_application.view_model.shared.footprint import VoiceFootprintViewModel
from sampletones_core.constants.enums import ChannelName, FeatureKey
from sampletones_core.exporters import Features, playing_channels, stands_by
from sampletones_core.features.envelope import Envelope
from sampletones_core.formats.famitracker.footprint import features_footprint
from sampletones_shared.types.callback import VoidCallback
from sampletones_shared.utils.callbacks import CallbackMixin


class PendingChangesProtocol(Protocol):
    """The changes a reader made that are still on their way to the open document.

    The panel shows what the document will hold, so every reading of a reconstruction's envelopes
    passes through the changes waiting to land.
    """

    def drawn(self, envelopes: ChannelEnvelopesViewModel) -> ChannelEnvelopesViewModel:
        """The document's envelopes with every change on its way written over them."""


class ReconstructionInstrumentsLogic(CallbackMixin):
    """What the instruments panel shows of the voice in front of it, and where an edit to it goes.

    A reconstruction's channel moved on the panel travels out as a :class:`ChannelChange`, which
    the document takes in its turn. Until it lands, the envelopes the panel draws and the figures
    measuring them read through the changes on their way, so they answer for what the document
    will hold.
    """

    def __init__(
        self,
        editor: InstrumentEditingProtocol,
        pending_changes: PendingChangesProtocol,
    ) -> None:
        self._editor = editor
        self._pending_changes = pending_changes

        self._silenced: Set[ChannelName] = set()

        self.on_view_changed: Optional[Callable[[ReconstructionInstrumentsViewModel], None]] = None
        self.on_feature_data_changed: Optional[Callable[[Optional[ChannelEnvelopesViewModel]], None]] = None
        self.on_channel_changed: Optional[Callable[[ChannelChange], None]] = None
        self.on_display_refreshed: Optional[VoidCallback] = None

    def update_display(self) -> None:
        """Renders whatever the panel has in front of it, envelopes and figures together.

        A document opened, a recording removed and a new choice of what is heard each change what
        the panel shows, so each redraws it from the document. The cards beside the panel describe
        the same voice, so the render is reported once it has been made and they settle on it: an
        edit to an instrument redraws its waveform here.
        """
        self.call(self.on_view_changed, self._build_view_model(self._measured_channels()))
        self.call(self.on_feature_data_changed, self._displayed_features())
        self.call(self.on_display_refreshed)

    def _displayed_features(self) -> Optional[ChannelEnvelopesViewModel]:
        """The envelopes the panel plots: a reconstruction's channels, or an instrument's own set.

        An instrument is drawn on the tab the panel shows it under, which is the channel offering every
        dimension an instrument writes, and it answers to no recording, so it carries no stretches.
        """
        instrument = self.instrument_edit
        if instrument is not None:
            return ChannelEnvelopesViewModel(
                channels=self._instrument_channels(instrument),
                ownership={},
            )

        return self._reconstruction_envelopes()

    @staticmethod
    def _instrument_channels(
        instrument: InstrumentEdit,
    ) -> Dict[ChannelName, Features]:
        """An instrument's envelopes under the channel the panel shows it on."""
        return {INSTRUMENT_CHANNEL: instrument.features}

    def refresh_view(self) -> None:
        """Reports which channels play and the sizes they occupy, redrawing only a channel an edit silenced.

        This answers a document whose envelopes the panel already draws: a regeneration of the
        panel's own edit, or a retune, which carries every envelope over. The byte figures and the
        standing-by channels settle on what an instrument now exports, and the envelopes stay as
        drawn, so a field the user is still typing in keeps what they wrote. A channel the edit
        silenced stands by in the document once the regeneration lands, holding no frame, so the
        panel draws it empty and the next edit starts from what the document holds. A document
        rewritten anywhere else is drawn whole through :meth:`update_display`.
        """
        self.call(
            self.on_view_changed,
            self._build_view_model(self._measured_channels()),
        )
        self._redraw_silenced()

    def _redraw_silenced(self) -> None:
        """Draws the channels an edit silenced as the document now holds them, once they stand by there."""
        envelopes = self._reconstruction_envelopes()
        if envelopes is None:
            return

        standing = {
            channel_name: envelopes[channel_name]
            for channel_name in self._silenced
            if not envelopes[channel_name].has_frames
        }
        if not standing:
            return

        self._silenced.difference_update(standing)
        self.call(
            self.on_feature_data_changed,
            ChannelEnvelopesViewModel(
                channels=standing,
                ownership={
                    channel_name: lane for channel_name, lane in envelopes.ownership.items() if channel_name in standing
                },
            ),
        )

    def _measured_channels(self) -> Optional[Dict[ChannelName, Features]]:
        """The channels of the reconstruction in front of the panel, as its figures measure them.

        A channel measures as the document will hold it once the changes on their way land. A
        change silencing every frame of a channel leaves it standing by, so that channel measures
        standing by from the moment the change is made, with no frame and no figure.
        """
        document = self._document_envelopes()
        if document is None:
            return None

        return {
            channel_name: (
                features if features == document[channel_name] else self._as_regenerated(channel_name, features)
            )
            for channel_name, features in self._pending_changes.drawn(document).channels.items()
        }

    @staticmethod
    def _as_regenerated(channel_name: ChannelName, features: Features) -> Features:
        """The envelopes a channel holds once the regeneration has rebuilt it from ``features``.

        A channel the envelopes silence rests through every frame, which the document stands by,
        describing no frame.
        """
        if stands_by(channel_name, features):
            return features.leave_to_channel(features.envelopes)

        return features

    def _reconstruction_envelopes(self) -> Optional[ChannelEnvelopesViewModel]:
        """The envelopes of the reconstruction in front of the panel, the changes on their way included."""
        document = self._document_envelopes()
        return None if document is None else self._pending_changes.drawn(document)

    def _document_envelopes(self) -> Optional[ChannelEnvelopesViewModel]:
        """The envelopes the reconstruction in front of the panel holds, where it holds one and no instrument."""
        match self._editor.edited_instrument():
            case ChannelEnvelopesViewModel() as envelopes:
                return envelopes
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
            footprint=VoiceFootprintViewModel.from_instrument(features_footprint(instrument.features)),
            instrument=InstrumentViewModel(name=instrument.name),
        )

    def _build_footprint(
        self,
        channels: Dict[ChannelName, Features],
    ) -> VoiceFootprintViewModel:
        """Measures the raw size of each playing channel's instrument.

        Each instrument is measured at the whole lengths its own envelopes state. A channel standing
        by is written nowhere, so it is measured nowhere and the sample's total names the channels
        that play.
        """
        return VoiceFootprintViewModel.from_footprints(
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
        """Moves the pitch one channel of a reconstruction has its frames measured against.

        A conversion states the value it found, and moving it rebuilds the channel's frames around
        the new origin, so the edit travels back out as a change of that channel. The panel offers
        the pitch on a reconstruction's channels alone, so a change reaching it while it shows an
        instrument, or a voice that has gone, draws the panel as it now stands and goes nowhere.
        """
        match self._editor.edited_instrument():
            case ChannelEnvelopesViewModel() as document:
                self._change(
                    document,
                    ChannelChange(
                        channel_name=channel_name,
                        feature_key=FeatureKey.INITIAL_PITCH,
                        envelopes={},
                        initial_pitch=value,
                    ),
                )
            case _:
                self.update_display()

    def handle_envelope_changed(
        self,
        channel_name: ChannelName,
        feature_key: FeatureKey,
        envelope: Envelope[int],
    ) -> None:
        """Takes one dimension as an edit leaves it, values and loop point together.

        The panel states the whole dimension, so a bar redrawn on the plot and a sequence typed
        into the text field arrive the same way and are written the same way. An instrument stands
        on no audio, so an edit reaches it at once, while a reconstruction's dimension travels back
        out as a change of its channel. An edit reaching a panel whose voice has gone draws the
        panel as it now stands and goes nowhere.
        """
        match self._editor.edited_instrument():
            case InstrumentEdit():
                self._editor.write_envelope(feature_key, envelope)
                self.update_display()
            case ChannelEnvelopesViewModel() as document:
                self._change(
                    document,
                    ChannelChange(
                        channel_name=channel_name,
                        feature_key=feature_key,
                        envelopes={feature_key: envelope},
                        initial_pitch=None,
                    ),
                )
            case None:
                self.update_display()

    def _change(self, document: ChannelEnvelopesViewModel, change: ChannelChange) -> None:
        """Sends a change on to the document, and reports the figures it leaves at once.

        The channel is read as the change leaves it before the change goes, so whether it
        silences the channel is known by the time the rebuild lands. The figures are reported
        afterwards, measuring what the edit leaves ahead of its rebuild.

        Args:
            document: The envelopes the open document holds.
            change: What the reader moved.
        """
        drawn = self._pending_changes.drawn(document)
        self._note_silenced(change.channel_name, change.rebased(drawn[change.channel_name]))
        self.call(self.on_channel_changed, change)
        self.call(self.on_view_changed, self._build_view_model(self._measured_channels()))

    def _note_silenced(self, channel_name: ChannelName, features: Features) -> None:
        """Remembers whether the latest edit of a channel silences it, which its rebuild then shows."""
        if stands_by(channel_name, features):
            self._silenced.add(channel_name)
        else:
            self._silenced.discard(channel_name)
