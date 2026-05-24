from typing import Callable, Optional

import dearpygui.dearpygui as dpg

from sampletones_core.audio import AudioDeviceManager
from sampletones_shared.exceptions import PlaybackError
from sampletones_shared.types.callback import VoidCallback

from ..constants.player import (
    DIM_PANEL_HEIGHT_PLAYER,
    DIM_PANEL_WIDTH_PLAYER,
    DIM_TABLE_HEIGHT_PLAYER_CONTROLS,
    LBL_BUTTON_PLAYER_PAUSE,
    LBL_BUTTON_PLAYER_PLAY,
    LBL_BUTTON_PLAYER_RESUME,
    LBL_BUTTON_PLAYER_STOP,
    LBL_TEXT_PLAYER_POSITION,
    LBL_TEXT_PLAYER_SAMPLES,
    MSG_PLAYER_AUDIO_PLAYBACK_ERROR,
    MSG_PLAYER_NO_AUDIO_LOADED,
    SUF_PLAYER_CONTROLS_GROUP,
    SUF_PLAYER_ERROR_POPUP,
    SUF_PLAYER_NO_AUDIO_POPUP,
    SUF_PLAYER_PAUSE,
    SUF_PLAYER_PLAY,
    SUF_PLAYER_POSITION,
    SUF_PLAYER_STOP,
    TTL_DIALOG_PLAYER_NO_AUDIO,
)
from ..elements.button import GUIButton
from ..elements.panel import GUIPanel
from ..player.data import AudioData
from ..player.player import AudioPlayer
from ..utils.align import table_wrapper
from ..utils.dialogs import show_error_dialog, show_modal_dialog
from ..utils.dpg import dpg_configure_item, dpg_set_item_callback, dpg_set_item_label, dpg_set_value


class GUIAudioPlayerPanel(GUIPanel):
    def __init__(
        self,
        tag: str,
        parent: str,
        audio_device_manager: AudioDeviceManager,
        on_position_changed: Optional[Callable[[int], None]] = None,
        on_change_audio_state: Optional[VoidCallback] = None,
    ):
        self.audio_device_manager = audio_device_manager

        self.play_button_tag = f"{tag}{SUF_PLAYER_PLAY}"
        self.pause_button_tag = f"{tag}{SUF_PLAYER_PAUSE}"
        self.stop_button_tag = f"{tag}{SUF_PLAYER_STOP}"
        self.position_text_tag = f"{tag}{SUF_PLAYER_POSITION}"
        self.controls_group_tag = f"{tag}{SUF_PLAYER_CONTROLS_GROUP}"

        self.no_audio_popup_tag = f"{tag}{SUF_PLAYER_NO_AUDIO_POPUP}"
        self.error_popup_tag = f"{tag}{SUF_PLAYER_ERROR_POPUP}"

        self.on_position_changed: Optional[Callable[[int], None]] = on_position_changed

        self.audio_player = AudioPlayer(
            audio_device_manager,
            on_position_changed=self._on_position_changed,
            on_change_audio_state=on_change_audio_state,
        )

        super().__init__(
            tag=tag,
            parent=parent,
            width=DIM_PANEL_WIDTH_PLAYER,
            height=DIM_PANEL_HEIGHT_PLAYER,
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
            border=False,
        ):
            self._create_controls()
            dpg.add_text(MSG_PLAYER_NO_AUDIO_LOADED, tag=self.position_text_tag)

    @table_wrapper(columns=3, height=DIM_TABLE_HEIGHT_PLAYER_CONTROLS)
    def _create_controls(self) -> None:
        GUIButton(
            tag=self.play_button_tag,
            label=LBL_BUTTON_PLAYER_PLAY,
            callback=self.play,
            enabled=False,
            width=-1,
        )
        GUIButton(
            tag=self.pause_button_tag,
            label=LBL_BUTTON_PLAYER_PAUSE,
            callback=self.pause,
            enabled=False,
            width=-1,
        )
        GUIButton(
            tag=self.stop_button_tag,
            label=LBL_BUTTON_PLAYER_STOP,
            callback=self.stop,
            enabled=False,
            width=-1,
        )

    def disable(self) -> None:
        dpg_configure_item(self.controls_group_tag, enabled=False)

    def enable(self) -> None:
        dpg_configure_item(self.controls_group_tag, enabled=True)

    def load_audio_data(self, audio_data: AudioData) -> None:
        self.audio_player.load_audio_data(audio_data)
        self._update_controls()

    def clear_audio(self) -> None:
        self.audio_player.clear_audio()
        self._update_controls()

    def play(self) -> None:
        try:
            self.audio_player.play()
        except PlaybackError as exception:
            show_error_dialog(exception, MSG_PLAYER_AUDIO_PLAYBACK_ERROR)
            return

        self._update_controls()

    def pause_or_resume(self) -> None:
        if not self.audio_player.is_playing:
            return self.play()

        if self.audio_player.is_paused:
            return self.resume()

        return self.pause()

    def pause(self) -> None:
        self.audio_player.pause()
        self._update_controls()

    def resume(self) -> None:
        self.audio_player.resume()
        self._update_controls()

    def stop(self) -> None:
        self.audio_player.stop()
        self._update_controls()

    def is_loaded(self) -> bool:
        return self.audio_player.audio_data.is_loaded()

    def is_playing(self) -> bool:
        return self.audio_player.is_playing

    def is_paused(self) -> bool:
        return self.audio_player.is_paused

    def _on_position_changed(self, position: int) -> None:
        self._update_position_display()
        self.call(self.on_position_changed, position)

    def _update_controls(self) -> None:
        has_audio = self.audio_player.audio_data.is_loaded()

        if has_audio:
            is_playing = self.audio_player.is_playing
            is_paused = self.audio_player.is_paused

            dpg_configure_item(self.play_button_tag, enabled=True)
            dpg_configure_item(self.pause_button_tag, enabled=is_playing or is_paused)
            dpg_configure_item(self.stop_button_tag, enabled=True)

            if is_paused:
                dpg_set_item_label(self.pause_button_tag, LBL_BUTTON_PLAYER_RESUME)
                dpg_set_item_callback(self.pause_button_tag, self.resume)
            else:
                dpg_set_item_label(self.pause_button_tag, LBL_BUTTON_PLAYER_PAUSE)
                dpg_set_item_callback(self.pause_button_tag, self.pause)
        else:
            dpg_configure_item(self.play_button_tag, enabled=False)
            dpg_configure_item(self.pause_button_tag, enabled=False)
            dpg_configure_item(self.stop_button_tag, enabled=False)

        self._update_position_display()

    def _update_position_display(self) -> None:
        if not self.audio_player.audio_data.is_loaded():
            dpg_set_value(self.position_text_tag, MSG_PLAYER_NO_AUDIO_LOADED)
            return

        position_text = (
            f"{LBL_TEXT_PLAYER_POSITION}{self.audio_player.audio_data.current_position}"
            f"/{self.audio_player.audio_data.samples}{LBL_TEXT_PLAYER_SAMPLES}"
        )
        dpg_set_value(self.position_text_tag, position_text)

    def _show_no_audio_dialog(self) -> None:
        def content(parent: str) -> None:
            dpg.add_text(MSG_PLAYER_NO_AUDIO_LOADED, parent=parent)

        show_modal_dialog(
            tag=self.no_audio_popup_tag,
            title=TTL_DIALOG_PLAYER_NO_AUDIO,
            content=content,
        )
