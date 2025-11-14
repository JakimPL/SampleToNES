from typing import Callable, Optional

import dearpygui.dearpygui as dpg

from sampletones.audio.manager import AudioDeviceManager

from ..constants import (
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
)
from ..elements.button import GUIButton
from ..elements.panel import GUIPanel
from ..player.data import AudioData
from ..player.player import AudioPlayer, PlaybackError
from ..utils.common import (
    dpg_configure_item,
    dpg_set_item_callback,
    dpg_set_item_label,
    dpg_set_value,
)
from ..utils.dialogs import show_error_dialog, show_modal_dialog


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
            parent=parent,
            width=DIM_PLAYER_PANEL_WIDTH,
            height=DIM_PLAYER_PANEL_HEIGHT,
            init=True,
        )

    def create_panel(self) -> None:
        with dpg.child_window(
            tag=self.tag,
            parent=self.parent,
            width=self.width,
            height=self.height,
            no_scroll_with_mouse=True,
            no_scrollbar=True,
        ):
            with dpg.group(tag=self.controls_group_tag, horizontal=True):
                GUIButton(
                    tag=self.play_button_tag,
                    label=LBL_PLAYER_BUTTON_PLAY,
                    callback=self._play_audio,
                    enabled=False,
                    width=DIM_PLAYER_BUTTON_WIDTH,
                )
                GUIButton(
                    tag=self.pause_button_tag,
                    label=LBL_PLAYER_BUTTON_PAUSE,
                    callback=self._pause_audio,
                    enabled=False,
                    width=DIM_PLAYER_BUTTON_WIDTH,
                )
                GUIButton(
                    tag=self.stop_button_tag,
                    label=LBL_PLAYER_BUTTON_STOP,
                    callback=self._stop_audio,
                    enabled=False,
                    width=DIM_PLAYER_BUTTON_WIDTH,
                )
            dpg.add_text(MSG_PLAYER_NO_AUDIO_LOADED, tag=self.position_text_tag)

    def disable(self) -> None:
        dpg_configure_item(self.controls_group_tag, enabled=False)

    def enable(self) -> None:
        dpg_configure_item(self.controls_group_tag, enabled=True)

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
        except PlaybackError as exception:
            show_error_dialog(exception, MSG_PLAYER_AUDIO_PLAYBACK_ERROR)
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

            dpg_configure_item(self.play_button_tag, enabled=True)
            dpg_configure_item(self.pause_button_tag, enabled=is_playing or is_paused)
            dpg_configure_item(self.stop_button_tag, enabled=True)

            if is_paused:
                dpg_set_item_label(self.pause_button_tag, LBL_PLAYER_BUTTON_RESUME)
                dpg_set_item_callback(self.pause_button_tag, self._resume_audio)
            else:
                dpg_set_item_label(self.pause_button_tag, LBL_PLAYER_BUTTON_PAUSE)
                dpg_set_item_callback(self.pause_button_tag, self._pause_audio)
        else:
            dpg_configure_item(self.play_button_tag, enabled=False)
            dpg_configure_item(self.pause_button_tag, enabled=False)
            dpg_configure_item(self.stop_button_tag, enabled=False)

    def _update_position_display(self) -> None:
        if not self.audio_player.audio_data:
            dpg_set_value(self.position_text_tag, MSG_PLAYER_NO_AUDIO_LOADED)
        else:
            position_text = f"{PFX_PLAYER_POSITION}{self.audio_player.audio_data.current_position}/{self.audio_player.audio_data.samples}{SUF_PLAYER_SAMPLES}"
            dpg_set_value(self.position_text_tag, position_text)

    def _show_no_audio_dialog(self) -> None:
        def content(parent: str) -> None:
            dpg.add_text(MSG_PLAYER_NO_AUDIO_LOADED, parent=parent)

        show_modal_dialog(
            tag=self.no_audio_popup_tag,
            title=TITLE_DIALOG_NO_AUDIO,
            content=content,
        )
