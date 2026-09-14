from typing import Callable, Optional

from sampletones_application.logic.shared.playback_priority import PlaybackPriority
from sampletones_application.utils.callbacks.queue import CallbackQueue
from sampletones_application.view_model.shared.audio_data import AudioData
from sampletones_core.audio import AudioDeviceManager
from sampletones_core.constants.audio import DEFAULT_SAMPLE_RATE, START_OF_AUDIO
from sampletones_shared.exceptions import PlaybackError
from sampletones_shared.types.callback import VoidCallback
from sampletones_shared.utils.callbacks import CallbackMixin


class AudioPlayer(CallbackMixin):
    def __init__(
        self,
        audio_device_manager: AudioDeviceManager,
        *,
        sample_rate: int = DEFAULT_SAMPLE_RATE,
        on_position_changed: Optional[Callable[[int], None]] = None,
        on_change_audio_state: Optional[VoidCallback] = None,
    ):
        self.audio_device_manager = audio_device_manager
        self.audio_data: AudioData = AudioData.empty(sample_rate)

        self.on_position_changed = on_position_changed
        self.on_change_audio_state = on_change_audio_state

    @property
    def current_position(self) -> int:
        """Where this player's own playback stands on the device, sounding or held paused."""
        return self.audio_device_manager.position_of(self)

    def load_audio_data(self, audio_data: AudioData) -> None:
        self.audio_data = audio_data
        self.audio_device_manager.replace_audio(audio_data.sample, owner=self)
        self._notify_audio_state_changed()

    def clear_audio(self) -> None:
        self.stop()
        self.audio_data = AudioData.empty(self.audio_data.sample_rate)

    def _on_device_position_changed(self, position: int) -> None:
        """Carries a report from the thread writing the audio to the render thread.

        The mark the report moves is a widget, so the report crosses the way every background result
        does. The device reports the start of the audio once, as it winds down, and a position past
        it after each buffer it writes.
        """
        CallbackQueue.add(self._report_position, position == START_OF_AUDIO)

    def _report_position(self, wound_down: bool) -> None:
        """Reports where the playback stands, read as the report arrives on the render thread.

        A report travels while the reader may seek, so the position is read from the device where the
        report arrives, and a report overtaken by a seek draws the seek. A playback winding down is
        also when the transport's labels follow the state it left.

        Args:
            wound_down: Whether the report is the device's last for the playback.
        """
        self.call(self.on_position_changed, self.current_position)
        if wound_down:
            self._notify_audio_state_changed()

    def seek(self, position: int) -> None:
        """Moves this player's own playback to a sample, whether it sounds or stands paused.

        The device reports positions as it writes, and a paused one writes nothing, so the player
        reports the sample it moved to, which carries the mark there during a pause as well.

        Args:
            position: The sample to move to, clamped to the audio.
        """
        if not self.is_playing:
            return

        self.audio_device_manager.set_position(position)
        self.call(self.on_position_changed, self.current_position)

    def play(self, *, start: int) -> None:
        """Takes the output and sounds the loaded audio from a sample.

        Args:
            start: The sample playback begins at, clamped to the audio.
        """
        if not self.audio_data.is_loaded():
            self._notify_audio_state_changed()
            return

        self.audio_device_manager.set_position_callback(
            self._on_device_position_changed,
        )
        audio = self.audio_data.sample

        try:
            self.audio_device_manager.play(
                audio,
                priority=PlaybackPriority.NORMAL,
                owner=self,
                start=start,
            )
        except ValueError as exception:
            raise PlaybackError(f"Audio playback failed: {exception}") from exception

        self._notify_audio_state_changed()

    def pause(self) -> None:
        self.audio_device_manager.pause()
        self._notify_audio_state_changed()

    def resume(self) -> None:
        self.audio_device_manager.resume()
        self._notify_audio_state_changed()

    def stop(self) -> None:
        self.audio_device_manager.stop()
        self.call(self.on_position_changed, START_OF_AUDIO)
        self._notify_audio_state_changed()

    @property
    def is_playing(self) -> bool:
        """Whether this player owns the live output, sounding or held paused.

        Engagement is read from ownership so the player reports itself active only while its own
        audio is on the device, leaving a preview or another source's playback to their owners.
        """
        return self.audio_device_manager.is_owned_by(self)

    @property
    def is_paused(self) -> bool:
        return self.audio_device_manager.is_owned_by(self) and self.audio_device_manager.is_paused()

    def _notify_audio_state_changed(self) -> None:
        self.call(self.on_change_audio_state)
