from typing import Callable, Optional

import numpy as np

from sampletones_application.config.managers.session import SessionManager
from sampletones_application.logic.project.controller import ProjectController
from sampletones_application.logic.reconstruction.editing import (
    InstrumentAuditionProtocol,
)
from sampletones_application.logic.shared.playback_priority import PlaybackPriority
from sampletones_core.audio import AudioDeviceManager
from sampletones_core.configs import Config
from sampletones_core.constants.enums import ChannelName, GeneratorName
from sampletones_core.features import generator_channel, speaks_in_periods
from sampletones_core.performance.audition import audition_audio
from sampletones_core.project.voices.instrument import Instrument
from sampletones_shared.constants.music import OCTAVE_OFFSET, OCTAVE_SEMITONES
from sampletones_shared.exceptions import PlaybackError
from sampletones_shared.logger import logger
from sampletones_shared.utils.callbacks import CallbackMixin


class InstrumentAuditionLogic(CallbackMixin):
    """Sounds the instrument the Reconstructions tab is showing, at the note a key names.

    An instrument stands on no recording, so hearing one means playing it: the tab states which
    generator to sound it on and a piano key states the note, and the two together name the frames
    the voice makes. The audition plays at preview priority, so it yields to playback the reader
    asked for and answers Stop the way every other preview does.
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

        self.on_audition_error: Optional[Callable[[Exception], None]] = None

    def sound(self, generator_name: GeneratorName, semitone: int) -> None:
        """Sounds the instrument in front of the tab on one generator, at one key of the keyboard.

        Args:
            generator_name: The generator the voice is heard on.
            semitone: How far the key pressed stands above the C of the octave in force.
        """
        instrument = self._editor.instrument
        if instrument is None:
            return

        channel_name = generator_channel(generator_name)
        audio = audition_audio(
            instrument,
            channel_name,
            self._audition_config(),
            pitch=self._sounding_pitch(instrument, channel_name, semitone),
        )
        if audio is None:
            return

        self._play(audio, instrument.id)

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
        try:
            self._audio_device_manager.play(
                audio,
                update=False,
                priority=PlaybackPriority.PREVIEW,
            )
        except (PlaybackError, ValueError) as exception:
            logger.error_with_traceback(
                exception,
                f"Failed to audition instrument: {voice_id}",
            )
            self.call(self.on_audition_error, exception)
