from typing import Callable, Optional

from sampletones_application.logic.shared.audio_player import AudioPlayer
from sampletones_application.view_model.shared.audio_data import AudioData
from sampletones_application.view_model.shared.player import PlayerViewModel
from sampletones_core.audio import AudioDeviceManager
from sampletones_core.constants.audio import START_OF_AUDIO
from sampletones_shared.types.callback import VoidCallback
from sampletones_shared.utils.callbacks import CallbackMixin


class PlayerLogic(CallbackMixin):
    def __init__(
        self,
        audio_device_manager: AudioDeviceManager,
        on_change_audio_state: Optional[VoidCallback] = None,
    ) -> None:
        self._audio_player = AudioPlayer(
            audio_device_manager,
            on_position_changed=self._on_position_changed,
            on_change_audio_state=on_change_audio_state,
        )
        self.on_view_changed: Optional[Callable[[PlayerViewModel], None]] = None
        self.on_position_changed: Optional[Callable[[int], None]] = None

    def load_audio_data(self, audio_data: AudioData) -> None:
        self._audio_player.load_audio_data(audio_data)
        self._emit_view()

    def clear_audio(self) -> None:
        self._audio_player.clear_audio()
        self._emit_view()

    def play(self) -> None:
        self._play(start=START_OF_AUDIO)

    def play_from(self, position: int) -> None:
        """Puts the playhead at a sample: an engaged player moves there and goes on sounding or stays
        paused, and an idle one starts sounding from there.

        Args:
            position: The sample the playhead is put at, clamped to the audio.
        """
        if self._audio_player.is_playing:
            self._audio_player.seek(position)
            return

        self._play(start=position)

    def pause(self) -> None:
        self._audio_player.pause()
        self._emit_view()

    def resume(self) -> None:
        self._audio_player.resume()
        self._emit_view()

    def stop(self) -> None:
        self._audio_player.stop()
        self._emit_view()

    def pause_or_resume(self) -> None:
        if not self._audio_player.is_playing:
            self.play()
        elif self._audio_player.is_paused:
            self.resume()
        else:
            self.pause()

    def is_loaded(self) -> bool:
        return self._audio_player.audio_data.is_loaded()

    def is_playing(self) -> bool:
        return self._audio_player.is_playing

    def is_paused(self) -> bool:
        return self._audio_player.is_paused

    def is_engaged(self) -> bool:
        """Whether this player owns the live output, sounding or held paused."""
        return self._audio_player.is_playing

    def _play(self, *, start: int) -> None:
        try:
            self._audio_player.play(start=start)
        finally:
            self._emit_view()

    def _on_position_changed(self, position: int) -> None:
        self._emit_view()
        self.call(self.on_position_changed, position)

    def _emit_view(self) -> None:
        if self.on_view_changed is not None:
            self.call(self.on_view_changed, self._build_viewmodel())

    def _build_viewmodel(self) -> PlayerViewModel:
        has_audio = self._audio_player.audio_data.is_loaded()
        current_position = self._audio_player.current_position if has_audio else 0
        total_samples = self._audio_player.audio_data.samples if has_audio else 0
        return PlayerViewModel(
            has_audio=has_audio,
            is_playing=self._audio_player.is_playing,
            is_paused=self._audio_player.is_paused,
            current_position=current_position,
            total_samples=total_samples,
        )
