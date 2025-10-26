from typing import Callable, Optional

import dearpygui.dearpygui as dpg

from browser.constants import (
    BUTTON_PAUSE,
    BUTTON_PLAY,
    BUTTON_STOP,
    MSG_AUDIO_PLAYBACK_ERROR,
    MSG_NO_AUDIO_LOADED,
    PLAYER_PANEL_HEIGHT,
)
from browser.player.data import AudioData
from constants import SAMPLE_RATE
from utils.audioio import play_audio


class AudioPlayerPanel:
    def __init__(
        self, tag: str, parent: Optional[str] = None, on_position_changed: Optional[Callable[[int], None]] = None
    ):
        self.tag = tag
        self.parent = parent
        self.on_position_changed = on_position_changed

        self.play_button_tag = f"{tag}_play"
        self.pause_button_tag = f"{tag}_pause"
        self.stop_button_tag = f"{tag}_stop"
        self.position_text_tag = f"{tag}_position"

        self.audio_data: AudioData = AudioData.empty(SAMPLE_RATE)
        self.is_playing = False

        self._create_panel()

    def _create_panel(self) -> None:
        kwargs = {"tag": self.tag, "height": PLAYER_PANEL_HEIGHT, "width": -1, "no_scrollbar": True}
        if self.parent:
            kwargs["parent"] = self.parent

        with dpg.child_window(**kwargs):
            with dpg.group(horizontal=True):
                dpg.add_button(label=BUTTON_PLAY, tag=self.play_button_tag, callback=self._play_audio, enabled=False)
                dpg.add_button(label=BUTTON_PAUSE, tag=self.pause_button_tag, callback=self._pause_audio, enabled=False)
                dpg.add_button(label=BUTTON_STOP, tag=self.stop_button_tag, callback=self._stop_audio, enabled=False)
                dpg.add_text(MSG_NO_AUDIO_LOADED, tag=self.position_text_tag)

    def load_audio_data(self, audio_data: AudioData) -> None:
        self.audio_data = audio_data
        self._update_controls()
        self._update_position_display()

    def clear_audio(self) -> None:
        self.audio_data = AudioData.empty(SAMPLE_RATE)
        self.is_playing = False
        self._update_controls()
        self._update_position_display()

    def set_position(self, position: int) -> None:
        if self.audio_data.is_loaded():
            self.audio_data.set_position(position)
            self._update_position_display()

    def _play_audio(self) -> None:
        if not self.audio_data.is_loaded():
            self._show_no_audio_dialog()
            return

        try:
            play_audio(self.audio_data.sample)
            self.is_playing = True
            self._update_controls()
        except Exception as exception:
            self._show_playback_error_dialog(str(exception))

    def _pause_audio(self) -> None:
        self.is_playing = False
        self._update_controls()

    def _stop_audio(self) -> None:
        if self.audio_data.is_loaded():
            self.audio_data.reset_position()
            self.is_playing = False
            self._update_controls()
            self._update_position_display()
            if self.on_position_changed:
                self.on_position_changed(0)

    def _update_controls(self) -> None:
        has_audio = self.audio_data.is_loaded()
        dpg.configure_item(self.play_button_tag, enabled=has_audio and not self.is_playing)
        dpg.configure_item(self.pause_button_tag, enabled=has_audio and self.is_playing)
        dpg.configure_item(self.stop_button_tag, enabled=has_audio)

    def _update_position_display(self) -> None:
        if not self.audio_data.is_loaded():
            dpg.set_value(self.position_text_tag, MSG_NO_AUDIO_LOADED)
        else:
            position_text = f"Position: {self.audio_data.current_position}/{self.audio_data.duration_samples} samples"
            dpg.set_value(self.position_text_tag, position_text)

    def _show_no_audio_dialog(self) -> None:
        with dpg.popup(dpg.last_item(), modal=True, tag=f"{self.tag}_no_audio_popup"):
            dpg.add_text(MSG_NO_AUDIO_LOADED)
            dpg.add_button(label="OK", callback=lambda: dpg.delete_item(f"{self.tag}_no_audio_popup"))

    def _show_playback_error_dialog(self, error_message: str) -> None:
        with dpg.popup(dpg.last_item(), modal=True, tag=f"{self.tag}_error_popup"):
            dpg.add_text(f"{MSG_AUDIO_PLAYBACK_ERROR}: {error_message}")
            dpg.add_button(label="OK", callback=lambda: dpg.delete_item(f"{self.tag}_error_popup"))
