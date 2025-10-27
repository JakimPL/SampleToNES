from typing import Callable, Optional

import dearpygui.dearpygui as dpg

from browser.constants import (
    DIM_PLAYER_PANEL_DEFAULT_WIDTH,
    DIM_PLAYER_PANEL_HEIGHT,
    LBL_BUTTON_OK,
    LBL_PLAYER_BUTTON_PAUSE,
    LBL_PLAYER_BUTTON_PLAY,
    LBL_PLAYER_BUTTON_STOP,
    MSG_PLAYER_AUDIO_PLAYBACK_ERROR,
    MSG_PLAYER_NO_AUDIO_LOADED,
    PFX_PLAYER_POSITION,
    SUF_PLAYER_CONTROLS_GROUP,
    SUF_PLAYER_ERROR_POPUP,
    SUF_PLAYER_NO_AUDIO_POPUP,
    SUF_PLAYER_PAUSE,
    SUF_PLAYER_PLAY,
    SUF_PLAYER_POSITION,
    SUF_PLAYER_SAMPLES,
    SUF_PLAYER_STOP,
)
from browser.player.data import AudioData
from constants import SAMPLE_RATE
from utils.audio.device import AudioDeviceManager
from utils.audio.io import clip_audio, stereo_to_mono


class AudioPlayerPanel:
    def __init__(
        self,
        tag: str,
        audio_device_manager: AudioDeviceManager,
        parent: Optional[str] = None,
        on_position_changed: Optional[Callable[[int], None]] = None,
    ):
        self.tag = tag
        self.parent = parent
        self.on_position_changed = on_position_changed
        self.audio_device_manager = audio_device_manager

        self.play_button_tag = f"{tag}{SUF_PLAYER_PLAY}"
        self.pause_button_tag = f"{tag}{SUF_PLAYER_PAUSE}"
        self.stop_button_tag = f"{tag}{SUF_PLAYER_STOP}"
        self.position_text_tag = f"{tag}{SUF_PLAYER_POSITION}"

        self.audio_data: AudioData = AudioData.empty(SAMPLE_RATE)
        self.is_playing = False

        self._create_panel()

    def _create_panel(self) -> None:
        kwargs = {
            "tag": self.tag,
            "height": DIM_PLAYER_PANEL_HEIGHT,
            "width": DIM_PLAYER_PANEL_DEFAULT_WIDTH,
            "no_scrollbar": True,
        }
        if self.parent:
            kwargs["parent"] = self.parent

        with dpg.child_window(**kwargs):
            controls_group_tag = f"{self.tag}{SUF_PLAYER_CONTROLS_GROUP}"
            with dpg.group(tag=controls_group_tag, horizontal=True):
                dpg.add_button(
                    label=LBL_PLAYER_BUTTON_PLAY, tag=self.play_button_tag, callback=self._play_audio, enabled=False
                )
                dpg.add_button(
                    label=LBL_PLAYER_BUTTON_PAUSE, tag=self.pause_button_tag, callback=self._pause_audio, enabled=False
                )
                dpg.add_button(
                    label=LBL_PLAYER_BUTTON_STOP, tag=self.stop_button_tag, callback=self._stop_audio, enabled=False
                )
            dpg.add_text(MSG_PLAYER_NO_AUDIO_LOADED, tag=self.position_text_tag)

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

        audio = self.audio_data.sample
        audio = stereo_to_mono(audio)
        audio = clip_audio(audio)

        self.audio_device_manager.start(audio)
        self.is_playing = True
        self._update_controls()

    def _pause_audio(self) -> None:
        self.audio_device_manager.pause()
        self.is_playing = False
        self._update_controls()

    def _stop_audio(self) -> None:
        self.audio_device_manager.stop()
        if self.audio_data.is_loaded():
            self.audio_data.reset_position()
        self.is_playing = False
        self._update_controls()
        self._update_position_display()
        if self.on_position_changed:
            self.on_position_changed(0)

    def _update_controls(self) -> None:
        has_audio = self.audio_data.is_loaded()

        controls_group_tag = f"{self.tag}{SUF_PLAYER_CONTROLS_GROUP}"
        dpg.configure_item(controls_group_tag, enabled=has_audio)

        if has_audio:
            dpg.configure_item(self.play_button_tag, enabled=not self.is_playing)
            dpg.configure_item(self.pause_button_tag, enabled=self.is_playing)
            dpg.configure_item(self.stop_button_tag, enabled=True)

    def _update_position_display(self) -> None:
        if not self.audio_data:
            dpg.set_value(self.position_text_tag, MSG_PLAYER_NO_AUDIO_LOADED)
        else:
            position_text = (
                f"{PFX_PLAYER_POSITION}{self.audio_data.current_position}/{self.audio_data.samples}{SUF_PLAYER_SAMPLES}"
            )
            dpg.set_value(self.position_text_tag, position_text)

    def _show_no_audio_dialog(self) -> None:
        with dpg.popup(dpg.last_item(), modal=True, tag=f"{self.tag}{SUF_PLAYER_NO_AUDIO_POPUP}"):
            dpg.add_text(MSG_PLAYER_NO_AUDIO_LOADED)
            dpg.add_button(
                label=LBL_BUTTON_OK, callback=lambda: dpg.delete_item(f"{self.tag}{SUF_PLAYER_NO_AUDIO_POPUP}")
            )

    def _show_playback_error_dialog(self, error_message: str) -> None:
        with dpg.popup(dpg.last_item(), modal=True, tag=f"{self.tag}{SUF_PLAYER_ERROR_POPUP}"):
            dpg.add_text(MSG_PLAYER_AUDIO_PLAYBACK_ERROR)
            dpg.add_button(label=LBL_BUTTON_OK, callback=lambda: dpg.delete_item(f"{self.tag}{SUF_PLAYER_ERROR_POPUP}"))
