from typing import Callable, Optional

import dearpygui.dearpygui as dpg

from sampletones_application.constants.player import (
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
from sampletones_application.logic.player.data import AudioData
from sampletones_application.logic.player.player import PlayerLogic
from sampletones_application.ui.elements.button import GUIButton
from sampletones_application.ui.elements.panel import GUIPanel
from sampletones_application.utils.align import table_wrapper
from sampletones_application.utils.dialogs import show_error_dialog, show_modal_dialog
from sampletones_application.utils.dpg import dpg_configure_item, dpg_set_item_label, dpg_set_value
from sampletones_application.view_model.player.player import PlayerViewModel
from sampletones_core.audio import AudioDeviceManager
from sampletones_shared.exceptions import PlaybackError
from sampletones_shared.types.callback import VoidCallback


class GUIAudioPlayerPanel(GUIPanel):
    def __init__(
        self,
        tag: str,
        parent: str,
        audio_device_manager: AudioDeviceManager,
        on_position_changed: Optional[Callable[[int], None]] = None,
        on_change_audio_state: Optional[VoidCallback] = None,
    ):
        self.play_button_tag = f"{tag}{SUF_PLAYER_PLAY}"
        self.pause_button_tag = f"{tag}{SUF_PLAYER_PAUSE}"
        self.stop_button_tag = f"{tag}{SUF_PLAYER_STOP}"
        self.position_text_tag = f"{tag}{SUF_PLAYER_POSITION}"
        self.controls_group_tag = f"{tag}{SUF_PLAYER_CONTROLS_GROUP}"

        self.no_audio_popup_tag = f"{tag}{SUF_PLAYER_NO_AUDIO_POPUP}"
        self.error_popup_tag = f"{tag}{SUF_PLAYER_ERROR_POPUP}"

        self.player_logic = PlayerLogic(audio_device_manager, on_change_audio_state)
        self.player_logic.on_view_changed = self.update_view
        self.player_logic.on_position_changed = on_position_changed

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
            callback=self.pause_or_resume,
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

    def update_view(self, viewmodel: PlayerViewModel) -> None:
        if not viewmodel.has_audio:
            dpg_configure_item(self.play_button_tag, enabled=False)
            dpg_configure_item(self.pause_button_tag, enabled=False)
            dpg_configure_item(self.stop_button_tag, enabled=False)
            dpg_set_value(self.position_text_tag, MSG_PLAYER_NO_AUDIO_LOADED)
            return

        dpg_configure_item(self.play_button_tag, enabled=True)
        dpg_configure_item(self.pause_button_tag, enabled=viewmodel.is_playing or viewmodel.is_paused)
        dpg_configure_item(self.stop_button_tag, enabled=True)

        if viewmodel.is_paused:
            dpg_set_item_label(self.pause_button_tag, LBL_BUTTON_PLAYER_RESUME)
        else:
            dpg_set_item_label(self.pause_button_tag, LBL_BUTTON_PLAYER_PAUSE)

        position_text = (
            f"{LBL_TEXT_PLAYER_POSITION}{viewmodel.current_position}"
            f"/{viewmodel.total_samples}{LBL_TEXT_PLAYER_SAMPLES}"
        )
        dpg_set_value(self.position_text_tag, position_text)

    def disable(self) -> None:
        dpg_configure_item(self.controls_group_tag, enabled=False)

    def enable(self) -> None:
        dpg_configure_item(self.controls_group_tag, enabled=True)

    def load(self, audio_data: AudioData) -> None:
        self.disable()
        self.player_logic.load_audio_data(audio_data)
        self.enable()

    def load_audio_data(self, audio_data: AudioData) -> None:
        self.player_logic.load_audio_data(audio_data)

    def clear_audio(self) -> None:
        self.player_logic.clear_audio()

    def play(self) -> None:
        try:
            self.player_logic.play()
        except PlaybackError as exception:
            show_error_dialog(exception, MSG_PLAYER_AUDIO_PLAYBACK_ERROR)

    def pause_or_resume(self) -> None:
        try:
            self.player_logic.pause_or_resume()
        except PlaybackError as exception:
            show_error_dialog(exception, MSG_PLAYER_AUDIO_PLAYBACK_ERROR)

    def pause(self) -> None:
        self.player_logic.pause()

    def resume(self) -> None:
        self.player_logic.resume()

    def stop(self) -> None:
        self.player_logic.stop()

    def is_loaded(self) -> bool:
        return self.player_logic.is_loaded()

    def is_playing(self) -> bool:
        return self.player_logic.is_playing()

    def is_paused(self) -> bool:
        return self.player_logic.is_paused()

    def _show_no_audio_dialog(self) -> None:
        def content(parent: str) -> None:
            dpg.add_text(MSG_PLAYER_NO_AUDIO_LOADED, parent=parent)

        show_modal_dialog(
            tag=self.no_audio_popup_tag,
            title=TTL_DIALOG_PLAYER_NO_AUDIO,
            content=content,
        )
