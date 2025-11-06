from typing import Callable, Optional

import dearpygui.dearpygui as dpg

from browser.panels.panel import GUIPanel
from browser.player.data import AudioData
from browser.player.player import AudioPlayer, PlaybackError
from browser.utils import show_modal_dialog
from constants.browser import (
    DIM_PLAYER_BUTTON_WIDTH,
    DIM_PLAYER_PANEL_HEIGHT,
    DIM_PLAYER_PANEL_WIDTH,
    LBL_PLAYER_BUTTON_PAUSE,
    LBL_PLAYER_BUTTON_PLAY,
    LBL_PLAYER_BUTTON_RESUME,
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
    TITLE_DIALOG_NO_AUDIO,
    TITLE_DIALOG_PLAYBACK_ERROR,
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

        self.audio_player = AudioPlayer(audio_device_manager, on_position_changed=self._on_position_update)

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
                    label=LBL_PLAYER_BUTTON_PLAY,
                    tag=self.play_button_tag,
                    callback=self._play_audio,
                    enabled=False,
                    width=DIM_PLAYER_BUTTON_WIDTH,
                )
                dpg.add_button(
                    label=LBL_PLAYER_BUTTON_PAUSE,
                    tag=self.pause_button_tag,
                    callback=self._pause_audio,
                    enabled=False,
                    width=DIM_PLAYER_BUTTON_WIDTH,
                )
                dpg.add_button(
                    label=LBL_PLAYER_BUTTON_STOP,
                    tag=self.stop_button_tag,
                    callback=self._stop_audio,
                    enabled=False,
                    width=DIM_PLAYER_BUTTON_WIDTH,
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

    def _on_position_update(self, position: int) -> None:
        self._update_position_display()
        self._update_controls()
        if self.on_position_changed:
            self.on_position_changed(position)

    def _play_audio(self) -> None:
        try:
            self.audio_player.play()
        except PlaybackError as error:
            self._show_playback_error_dialog(str(error))
            return

        self._update_controls()

    def _pause_audio(self) -> None:
        self.audio_player.pause()
        self._update_controls()
        self._update_position_display()

    def _resume_audio(self) -> None:
        self.audio_player.resume()
        self._update_controls()
        self._update_position_display()

    def _stop_audio(self) -> None:
        self.audio_player.stop()
        self._update_controls()
        self._update_position_display()

    def _update_controls(self) -> None:
        has_audio = self.audio_player.audio_data.is_loaded()

        if has_audio:
            is_playing = self.audio_player.is_playing
            is_paused = self.audio_player.is_paused

            dpg.configure_item(self.play_button_tag, enabled=True)
            dpg.configure_item(self.pause_button_tag, enabled=is_playing or is_paused)
            dpg.configure_item(self.stop_button_tag, enabled=True)

            if is_paused:
                dpg.set_item_label(self.pause_button_tag, LBL_PLAYER_BUTTON_RESUME)
                dpg.set_item_callback(self.pause_button_tag, self._resume_audio)
            else:
                dpg.set_item_label(self.pause_button_tag, LBL_PLAYER_BUTTON_PAUSE)
                dpg.set_item_callback(self.pause_button_tag, self._pause_audio)
        else:
            dpg.configure_item(self.play_button_tag, enabled=False)
            dpg.configure_item(self.pause_button_tag, enabled=False)
            dpg.configure_item(self.stop_button_tag, enabled=False)

    def _update_position_display(self) -> None:
        if not self.audio_player.audio_data:
            dpg.set_value(self.position_text_tag, MSG_PLAYER_NO_AUDIO_LOADED)
        else:
            position_text = f"{PFX_PLAYER_POSITION}{self.audio_player.audio_data.current_position}/{self.audio_player.audio_data.samples}{SUF_PLAYER_SAMPLES}"
            dpg.set_value(self.position_text_tag, position_text)

    def _show_no_audio_dialog(self) -> None:
        def content(parent: str) -> None:
            dpg.add_text(MSG_PLAYER_NO_AUDIO_LOADED, parent=parent)

        show_modal_dialog(
            tag=self.no_audio_popup_tag,
            title=TITLE_DIALOG_NO_AUDIO,
            content=content,
        )

    def _show_playback_error_dialog(self, error_message: str) -> None:
        def content(parent: str) -> None:
            dpg.add_text(f"{MSG_PLAYER_AUDIO_PLAYBACK_ERROR}: {error_message}", parent=parent)

        show_modal_dialog(
            tag=self.error_popup_tag,
            title=TITLE_DIALOG_PLAYBACK_ERROR,
            content=content,
        )
