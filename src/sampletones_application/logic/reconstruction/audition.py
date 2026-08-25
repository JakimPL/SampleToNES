from typing import Callable, Optional

import numpy as np

from sampletones_application.config.managers.session import SessionManager
from sampletones_application.constants.instruments import AUDITION_GENERATOR, AUDITION_TICKS
from sampletones_application.logic.project.controller import ProjectController
from sampletones_application.logic.reconstruction.editing import (
    InstrumentAuditionProtocol,
)
from sampletones_application.logic.shared.playback_priority import PlaybackPriority
from sampletones_application.utils.callbacks.queue import CallbackQueue
from sampletones_application.view_model.reconstruction.waveform import (
    InstrumentWaveformViewModel,
)
from sampletones_core.audio import AudioDeviceManager
from sampletones_core.configs import Config
from sampletones_core.constants.enums import ChannelName, GeneratorName
from sampletones_core.features import generator_channel, speaks_in_periods
from sampletones_core.performance.audition import audition_audio, audition_ticks
from sampletones_core.project.voices.instrument import Instrument
from sampletones_shared.constants.music import OCTAVE_OFFSET, OCTAVE_SEMITONES
from sampletones_shared.exceptions import PlaybackError
from sampletones_shared.logger import logger
from sampletones_shared.utils.callbacks import CallbackMixin


class InstrumentAuditionLogic(CallbackMixin):
    """Sounds and draws the instrument the Reconstructions tab is showing, on one generator.

    An instrument stands on no recording, so hearing one means playing it and seeing one means
    rendering it. Both read the same choice — the generator the reader is auditioning it as — so
    the choice is held here and what the plot card draws is what the note keys sound. The audition
    plays at preview priority, so it yields to playback the reader asked for and answers Stop the
    way every other preview does.
    """

    def __init__(
        self,
        editor: InstrumentAuditionProtocol,
        project_controller: ProjectController,
        session_manager: SessionManager,
        audio_device_manager: AudioDeviceManager,
    ) -> None:
        self._editor = editor
        self._controller = project_controller
        self._session_manager = session_manager
        self._audio_device_manager = audio_device_manager
        self._generator_name: GeneratorName = AUDITION_GENERATOR

        self.on_audition_error: Optional[Callable[[Exception], None]] = None
        self.on_waveform_changed: Optional[Callable[[Optional[InstrumentWaveformViewModel]], None]] = None
        self.on_position_changed: Optional[Callable[[int], None]] = None

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

    def sound(self, semitone: int) -> None:
        """Sounds the instrument in front of the tab at one key of the keyboard's two octaves.

        Args:
            semitone: How far the key pressed stands above the C of the octave in force.
        """
        instrument = self._editor.instrument
        if instrument is None:
            return

        channel_name = generator_channel(self._generator_name)
        audio = audition_audio(
            instrument,
            channel_name,
            self._audition_config(),
            pitch=self._sounding_pitch(instrument, channel_name, semitone),
            ticks=audition_ticks(instrument, cap=AUDITION_TICKS),
        )
        if audio is None:
            return

        self._play(audio, instrument.id)

    def _waveform(self) -> Optional[InstrumentWaveformViewModel]:
        """The audio the open instrument makes at the pitch it stands at, drawn as it sounds.

        The plot shows the voice as it is rather than at a note just pressed, so it is rendered at
        the pitch the instrument itself is measured against.
        """
        instrument = self._editor.instrument
        if instrument is None:
            return None

        channel_name = generator_channel(self._generator_name)
        config = self._audition_config()
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

    def _sounding_pitch(
        self,
        instrument: Instrument,
        channel_name: ChannelName,
        semitone: int,
    ) -> int:
        """The value the channel sounds the voice at, which is a note or a noise period.

        Two rows of keys name two octaves above the one in force, the way the tracker's own note
        entry reads them. The noise channel selects one of sixteen periods instead of naming
        notes, so a key there sounds the instrument at the period it states.
        """
        if speaks_in_periods(channel_name):
            return instrument.reference(channel_name)

        return (self._session_manager.octave + OCTAVE_OFFSET) * OCTAVE_SEMITONES + semitone

    def _audition_config(self) -> Config:
        settings = self._controller.project.settings
        return Config().with_library(
            nes_frequency=settings.nes_frequency,
            sample_rate=settings.sample_rate,
        )

    def _play(self, audio: np.ndarray, voice_id: str) -> None:
        """Sounds the rendering, following it with a cursor while the audition holds the output.

        A preview yields to playback the reader asked for, so the cursor is followed only once the
        audition has the device: an audition that stands aside leaves the mark of whatever is
        sounding where it is.
        """
        try:
            sounding = self._audio_device_manager.play(
                audio,
                update=True,
                priority=PlaybackPriority.PREVIEW,
                owner=self,
            )
        except (PlaybackError, ValueError) as exception:
            logger.error_with_traceback(
                exception,
                f"Failed to audition instrument: {voice_id}",
            )
            self.call(self.on_audition_error, exception)
            return

        if sounding:
            self._audio_device_manager.set_position_callback(self._on_device_position)

    def _on_device_position(self, position: int) -> None:
        """Carries the sounding position from the playback thread to the card that draws it.

        The device reports from the thread writing the audio, and the mark is a widget, so the
        report crosses to the render thread the way every other background result does. The device
        reports a final zero as it winds down, which is what takes the mark off the card.
        """
        CallbackQueue.add(self.call, self.on_position_changed, position)
