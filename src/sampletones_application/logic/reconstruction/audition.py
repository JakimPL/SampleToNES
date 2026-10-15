from typing import Callable, Optional

from sampletones_application.constants.instruments import AUDITION_GENERATOR, AUDITION_TICKS
from sampletones_application.logic.project.controller import ProjectController
from sampletones_application.logic.reconstruction.editing import (
    InstrumentAuditionProtocol,
)
from sampletones_application.view_model.reconstruction.waveform import (
    InstrumentWaveformViewModel,
)
from sampletones_core.constants.enums import ChannelName, GeneratorName
from sampletones_core.features import generator_channel
from sampletones_core.performance.audition import audition_audio, audition_ticks
from sampletones_shared.utils.callbacks import CallbackMixin


class InstrumentAuditionLogic(CallbackMixin):
    """Holds the generator the Reconstructions tab auditions an instrument on, and draws the instrument there.

    An instrument stands on no recording, so seeing one means rendering it. The plot card draws it on the
    generator the reader chose, and a key sounds it on the channel of that same generator, so what the card
    draws is what the note keys sound.
    """

    def __init__(
        self,
        editor: InstrumentAuditionProtocol,
        project_controller: ProjectController,
    ) -> None:
        self._editor = editor
        self._controller = project_controller
        self._generator_name: GeneratorName = AUDITION_GENERATOR

        self.on_waveform_changed: Optional[Callable[[Optional[InstrumentWaveformViewModel]], None]] = None

    @property
    def channel_name(self) -> ChannelName:
        """The channel of the generator the instrument is auditioned on."""
        return generator_channel(self._generator_name)

    def set_generator(self, generator_name: GeneratorName) -> None:
        """Takes the generator the voice is auditioned as, redrawing it as the one now chosen."""
        self._generator_name = generator_name
        self.refresh()

    def refresh(self) -> None:
        """States the waveform of whatever the tab has in front of it, which an instrument alone has.

        A recording draws the audio it was made from, so the card is left to it; an instrument is
        redrawn whenever its envelopes change, which is what keeps the picture answering the edit.
        """
        self.call(self.on_waveform_changed, self._waveform())

    def _waveform(self) -> Optional[InstrumentWaveformViewModel]:
        """The audio the open instrument makes at the pitch it stands at, drawn as it sounds.

        The plot shows the voice as it is rather than at a note just pressed, so it is rendered at
        the pitch the instrument itself is measured against.
        """
        instrument = self._editor.instrument
        if instrument is None:
            return None

        channel_name = self.channel_name
        config = self._controller.project.settings.synthesis_config()
        audio = audition_audio(
            instrument,
            channel_name,
            config,
            pitch=instrument.reference(channel_name),
            ticks=audition_ticks(instrument, cap=AUDITION_TICKS),
        )
        if audio is None:
            return None

        return InstrumentWaveformViewModel(
            name=instrument.name,
            channel_name=channel_name,
            audio=audio,
            frame_length=config.frame_length,
        )
