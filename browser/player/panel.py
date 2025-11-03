from typing import Callable, Optional

import dearpygui.dearpygui as dpg

from browser.panels.panel import GUIPanel
from browser.player.data import AudioData
from browser.player.player import AudioPlayer, PlaybackError
from constants.browser import (
    DIM_PLAYER_PANEL_HEIGHT,
    DIM_PLAYER_PANEL_WIDTH,
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
from utils.audio.device import AudioDeviceManager


class GUIAudioPlayerPanel(GUIPanel):
    def __init__(
        self,
        tag: str,
        parent: str,
        audio_device_manager: AudioDeviceManager,
        on_position_changed: Optional[Callable[[int], None]] = None,
    ):
        self.on_position_changed = on_position_changed
        self.audio_device_manager = audio_device_manager

        self.play_button_tag = f"{tag}{SUF_PLAYER_PLAY}"
        self.pause_button_tag = f"{tag}{SUF_PLAYER_PAUSE}"
        self.stop_button_tag = f"{tag}{SUF_PLAYER_STOP}"
        self.position_text_tag = f"{tag}{SUF_PLAYER_POSITION}"
        self.controls_group_tag = f"{tag}{SUF_PLAYER_CONTROLS_GROUP}"

        self.no_audio_popup_tag = f"{tag}{SUF_PLAYER_NO_AUDIO_POPUP}"
        self.error_popup_tag = f"{tag}{SUF_PLAYER_ERROR_POPUP}"

        self.audio_player = AudioPlayer(audio_device_manager, on_position_changed=self.on_position_changed)

        super().__init__(
            tag=tag,
            parent_tag=parent,
            width=DIM_PLAYER_PANEL_WIDTH,
            height=DIM_PLAYER_PANEL_HEIGHT,
            init=True,
        )

    def create_panel(self) -> None:
        with dpg.child_window(
            tag=self.tag,
            parent=self.parent_tag,
            width=self.width,
            height=self.height,
        ):
            with dpg.group(tag=self.controls_group_tag, horizontal=True):
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
        self.audio_player.load_audio_data(audio_data)
        self._update_controls()
        self._update_position_display()

    def clear_audio(self) -> None:
        self.audio_player.clear_audio()
        self._update_controls()
        self._update_position_display()

    def set_position(self, position: int) -> None:
        self.audio_player.set_position(position)
        self._update_position_display()

    def _play_audio(self) -> None:
        try:
            self.audio_player.play()
        except PlaybackError:
            self._show_playback_error_dialog("")
            return

        self._update_controls()

    def _pause_audio(self) -> None:
        self.audio_player.pause()
        self._update_controls()

    def _stop_audio(self) -> None:
        self.audio_player.stop()
        self._update_controls()
        self._update_position_display()

    def _update_controls(self) -> None:
        has_audio = self.audio_player.audio_data.is_loaded()

        dpg.configure_item(self.controls_group_tag, enabled=has_audio)

        if has_audio:
            dpg.configure_item(self.play_button_tag, enabled=not self.audio_player.is_playing)
            dpg.configure_item(self.pause_button_tag, enabled=self.audio_player.is_playing)
            dpg.configure_item(self.stop_button_tag, enabled=True)

    def _update_position_display(self) -> None:
        if not self.audio_player.audio_data:
            dpg.set_value(self.position_text_tag, MSG_PLAYER_NO_AUDIO_LOADED)
        else:
            position_text = f"{PFX_PLAYER_POSITION}{self.audio_player.audio_data.current_position}/{self.audio_player.audio_data.samples}{SUF_PLAYER_SAMPLES}"
            dpg.set_value(self.position_text_tag, position_text)

    def _show_no_audio_dialog(self) -> None:
        with dpg.popup(dpg.last_item(), modal=True, tag=self.no_audio_popup_tag):
            dpg.add_text(MSG_PLAYER_NO_AUDIO_LOADED)
            dpg.add_button(label=LBL_BUTTON_OK, callback=lambda: dpg.delete_item(self.no_audio_popup_tag))

    def _show_playback_error_dialog(self, error_message: str) -> None:
        with dpg.popup(dpg.last_item(), modal=True, tag=self.error_popup_tag):
            dpg.add_text(MSG_PLAYER_AUDIO_PLAYBACK_ERROR)
            dpg.add_button(label=LBL_BUTTON_OK, callback=lambda: dpg.delete_item(self.error_popup_tag))
