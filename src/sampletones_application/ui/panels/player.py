from typing import Callable, Optional

import dearpygui.dearpygui as dpg

from sampletones_application.constants.player import (
    SUF_PLAYER_CONTROLS_GROUP,
    SUF_PLAYER_ERROR_POPUP,
    SUF_PLAYER_NO_AUDIO_POPUP,
    SUF_PLAYER_PAUSE,
    SUF_PLAYER_PLAY,
    SUF_PLAYER_POSITION,
    SUF_PLAYER_STOP,
)
from sampletones_application.layout.player import PlayerLayout
from sampletones_application.logic.shared.player import PlayerLogic
from sampletones_application.text.elements.global_ import PlayerElements
from sampletones_application.text.hierarchy import Page, Panel, TextType
from sampletones_application.text.key import TextKey
from sampletones_application.text.manager import LanguageManager
from sampletones_application.ui.elements.button import GUIButton
from sampletones_application.ui.elements.panel import GUIPanel
from sampletones_application.utils.dialogs import DialogsRenderer
from sampletones_application.utils.dpg import dpg_configure_item, dpg_set_item_label, dpg_set_value
from sampletones_application.view_model.shared.audio_data import AudioData
from sampletones_application.view_model.shared.player import PlayerViewModel
from sampletones_shared.exceptions import PlaybackError


class GUIAudioPlayerPanel(GUIPanel):
    def __init__(
        self,
        tag: str,
        parent: str,
        player_logic: PlayerLogic,
        on_position_changed: Optional[Callable[[int], None]] = None,
        *,
        layout: PlayerLayout,
        language_manager: LanguageManager,
        dialogs: DialogsRenderer,
    ):
        self.play_button_tag = f"{tag}{SUF_PLAYER_PLAY}"
        self.pause_button_tag = f"{tag}{SUF_PLAYER_PAUSE}"
        self.stop_button_tag = f"{tag}{SUF_PLAYER_STOP}"
        self.position_text_tag = f"{tag}{SUF_PLAYER_POSITION}"
        self.controls_group_tag = f"{tag}{SUF_PLAYER_CONTROLS_GROUP}"

        self.no_audio_popup_tag = f"{tag}{SUF_PLAYER_NO_AUDIO_POPUP}"
        self.error_popup_tag = f"{tag}{SUF_PLAYER_ERROR_POPUP}"

        self.player_logic = player_logic
        self.player_logic.on_view_changed = self.update_view
        self.player_logic.on_position_changed = on_position_changed

        self._dialogs = dialogs
        self._layout = layout
        self._lbl_play = language_manager[TextKey(Page.GLOBAL, Panel.PLAYER, TextType.LABEL, PlayerElements.PLAY)]
        self._lbl_pause = language_manager[TextKey(Page.GLOBAL, Panel.PLAYER, TextType.LABEL, PlayerElements.PAUSE)]
        self._lbl_resume = language_manager[TextKey(Page.GLOBAL, Panel.PLAYER, TextType.LABEL, PlayerElements.RESUME)]
        self._lbl_stop = language_manager[TextKey(Page.GLOBAL, Panel.PLAYER, TextType.LABEL, PlayerElements.STOP)]
        self._lbl_position = language_manager[
            TextKey(Page.GLOBAL, Panel.PLAYER, TextType.LABEL, PlayerElements.POSITION_PREFIX)
        ]
        self._lbl_samples = language_manager[
            TextKey(Page.GLOBAL, Panel.PLAYER, TextType.LABEL, PlayerElements.SAMPLES_SUFFIX)
        ]
        self._msg_no_audio = language_manager[
            TextKey(Page.GLOBAL, Panel.PLAYER, TextType.MESSAGE, PlayerElements.NO_AUDIO_LOADED)
        ]
        self._msg_playback_error = language_manager[
            TextKey(Page.GLOBAL, Panel.PLAYER, TextType.MESSAGE, PlayerElements.AUDIO_PLAYBACK_ERROR)
        ]
        self._ttl_no_audio = language_manager[
            TextKey(Page.GLOBAL, Panel.PLAYER, TextType.TITLE, PlayerElements.NO_AUDIO_DIALOG_TITLE)
        ]

        super().__init__(
            tag=tag,
            parent=parent,
            width=layout.panel.width,
            height=layout.panel.height,
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
            dpg.add_text(self._msg_no_audio, tag=self.position_text_tag)

    def _create_controls(self) -> None:
        with dpg.table(
            header_row=False,
            policy=dpg.mvTable_SizingStretchSame,
            resizable=False,
            width=-1,
            height=self._layout.controls_table.height,
        ):
            for _ in range(3):
                dpg.add_table_column()
            with dpg.table_row():
                GUIButton(
                    tag=self.play_button_tag,
                    label=self._lbl_play,
                    callback=self.play,
                    enabled=False,
                    width=-1,
                )
                GUIButton(
                    tag=self.pause_button_tag,
                    label=self._lbl_pause,
                    callback=self.pause_or_resume,
                    enabled=False,
                    width=-1,
                )
                GUIButton(
                    tag=self.stop_button_tag,
                    label=self._lbl_stop,
                    callback=self.stop,
                    enabled=False,
                    width=-1,
                )

    def update_view(self, viewmodel: PlayerViewModel) -> None:
        if not viewmodel.has_audio:
            dpg_configure_item(self.play_button_tag, enabled=False)
            dpg_configure_item(self.pause_button_tag, enabled=False)
            dpg_configure_item(self.stop_button_tag, enabled=False)
            dpg_set_value(self.position_text_tag, self._msg_no_audio)
            return

        dpg_configure_item(self.play_button_tag, enabled=True)
        dpg_configure_item(self.pause_button_tag, enabled=viewmodel.is_playing or viewmodel.is_paused)
        dpg_configure_item(self.stop_button_tag, enabled=True)

        if viewmodel.is_paused:
            dpg_set_item_label(self.pause_button_tag, self._lbl_resume)
        else:
            dpg_set_item_label(self.pause_button_tag, self._lbl_pause)

        position_text = (
            f"{self._lbl_position}{viewmodel.current_position}" f"/{viewmodel.total_samples}{self._lbl_samples}"
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
            self._dialogs.show_error(exception, self._msg_playback_error)

    def pause_or_resume(self) -> None:
        try:
            self.player_logic.pause_or_resume()
        except PlaybackError as exception:
            self._dialogs.show_error(exception, self._msg_playback_error)

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
            dpg.add_text(self._msg_no_audio, parent=parent)

        self._dialogs.show_modal(
            tag=self.no_audio_popup_tag,
            title=self._ttl_no_audio,
            content=content,
        )
