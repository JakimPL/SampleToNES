from typing import Callable, Optional

import dearpygui.dearpygui as dpg

from browser.constants import (
    BUTTON_OK,
    BUTTON_PAUSE,
    BUTTON_PLAY,
    BUTTON_STOP,
    MSG_AUDIO_PLAYBACK_ERROR,
    MSG_NO_AUDIO_LOADED,
    PLAYER_CONTROLS_GROUP_SUFFIX,
    PLAYER_ERROR_POPUP_SUFFIX,
    PLAYER_NO_AUDIO_POPUP_SUFFIX,
    PLAYER_PANEL_DEFAULT_WIDTH,
    PLAYER_PANEL_HEIGHT,
    PLAYER_PAUSE_SUFFIX,
    PLAYER_PLAY_SUFFIX,
    PLAYER_POSITION_PREFIX,
    PLAYER_POSITION_SUFFIX,
    PLAYER_SAMPLES_SUFFIX,
    PLAYER_STOP_SUFFIX,
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

        self.play_button_tag = f"{tag}{PLAYER_PLAY_SUFFIX}"
        self.pause_button_tag = f"{tag}{PLAYER_PAUSE_SUFFIX}"
        self.stop_button_tag = f"{tag}{PLAYER_STOP_SUFFIX}"
        self.position_text_tag = f"{tag}{PLAYER_POSITION_SUFFIX}"

        self.audio_data: AudioData = AudioData.empty(SAMPLE_RATE)
        self.is_playing = False

        self._create_panel()

    def _create_panel(self) -> None:
        kwargs = {
            "tag": self.tag,
            "height": PLAYER_PANEL_HEIGHT,
            "width": PLAYER_PANEL_DEFAULT_WIDTH,
            "no_scrollbar": True,
        }
        if self.parent:
            kwargs["parent"] = self.parent

        with dpg.child_window(**kwargs):
            controls_group_tag = f"{self.tag}{PLAYER_CONTROLS_GROUP_SUFFIX}"
            with dpg.group(horizontal=True, tag=controls_group_tag, enabled=False):
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

        controls_group_tag = f"{self.tag}{PLAYER_CONTROLS_GROUP_SUFFIX}"
        dpg.configure_item(controls_group_tag, enabled=has_audio)

        if has_audio:
            dpg.configure_item(self.play_button_tag, enabled=not self.is_playing)
            dpg.configure_item(self.pause_button_tag, enabled=self.is_playing)
            dpg.configure_item(self.stop_button_tag, enabled=True)

    def _update_position_display(self) -> None:
        if not self.audio_data.is_loaded():
            dpg.set_value(self.position_text_tag, MSG_NO_AUDIO_LOADED)
        else:
            position_text = f"{PLAYER_POSITION_PREFIX}{self.audio_data.current_position}/{self.audio_data.samples}{PLAYER_SAMPLES_SUFFIX}"
            dpg.set_value(self.position_text_tag, position_text)

    def _show_no_audio_dialog(self) -> None:
        with dpg.popup(dpg.last_item(), modal=True, tag=f"{self.tag}{PLAYER_NO_AUDIO_POPUP_SUFFIX}"):
            dpg.add_text(MSG_NO_AUDIO_LOADED)
            dpg.add_button(
                label=BUTTON_OK, callback=lambda: dpg.delete_item(f"{self.tag}{PLAYER_NO_AUDIO_POPUP_SUFFIX}")
            )

    def _show_playback_error_dialog(self, error_message: str) -> None:
        with dpg.popup(dpg.last_item(), modal=True, tag=f"{self.tag}{PLAYER_ERROR_POPUP_SUFFIX}"):
            dpg.add_text(f"{MSG_AUDIO_PLAYBACK_ERROR}: {error_message}")
            dpg.add_button(label=BUTTON_OK, callback=lambda: dpg.delete_item(f"{self.tag}{PLAYER_ERROR_POPUP_SUFFIX}"))
