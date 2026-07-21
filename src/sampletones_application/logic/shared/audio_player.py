from typing import Callable, Optional

from sampletones_application.logic.shared.playback_priority import PlaybackPriority
from sampletones_application.view_model.shared.audio_data import AudioData
from sampletones_core.audio import AudioDeviceManager
from sampletones_core.constants.audio import DEFAULT_SAMPLE_RATE
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
        self._current_position: int = 0

        self.on_position_changed = on_position_changed
        self.on_change_audio_state = on_change_audio_state

    @property
    def current_position(self) -> int:
        return self._current_position

    def load_audio_data(self, audio_data: AudioData) -> None:
        self.audio_data = audio_data
        self.audio_device_manager.replace_audio(audio_data.sample, owner=self)
        self._notify_audio_state_changed()

    def clear_audio(self) -> None:
        self.stop()
        self.audio_data = AudioData.empty(self.audio_data.sample_rate)

    def _set_current_position(self, position: int) -> None:
        self._current_position = max(
            0,
            min(
                position,
                self.audio_data.samples,
            ),
        )

    def _on_device_position_changed(self, position: int) -> None:
        if self.audio_data.is_loaded():
            self._set_current_position(position)
            self.call(self.on_position_changed, position)

        if position == 0:
            self._notify_audio_state_changed()

    def set_position(self, position: int) -> None:
        if self.audio_data.is_loaded():
            self._set_current_position(position)
            self.audio_device_manager.set_position(position)
            self.call(self.on_position_changed, position)

    def play(self) -> None:
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
        if self.audio_data.is_loaded():
            self._current_position = 0

        self.call(self.on_position_changed, 0)
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
