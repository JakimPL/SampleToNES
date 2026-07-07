from typing import Optional

import dearpygui.dearpygui as dpg

from sampletones_application.categories.elements.global_ import PlayerElements
from sampletones_application.categories.hierarchy import Page, Panel, TextType
from sampletones_application.categories.manager import LanguageManager
from sampletones_application.constants.general import TAG_GLOBAL_THEME_PLAYER_TOOLBAR
from sampletones_application.constants.player import (
    SUF_PLAYER_PAUSE,
    SUF_PLAYER_PLAY,
    SUF_PLAYER_POSITION,
    SUF_PLAYER_STOP,
)
from sampletones_application.layout.player import PlayerLayout
from sampletones_application.ui.elements.button import GUIButton
from sampletones_application.ui.elements.panel import GUIPanel
from sampletones_application.ui.themes.registry import ThemeRegistry
from sampletones_application.utils.gui.dpg import (
    dpg_configure_item,
    dpg_set_item_label,
    dpg_set_value,
)
from sampletones_application.view_model.shared.player import PlayerViewModel
from sampletones_shared.types.callback import VoidCallback


class GUIAudioPlayerPanel(GUIPanel):
    def __init__(
        self,
        tag: str,
        parent: str,
        *,
        layout: PlayerLayout,
        language_manager: LanguageManager,
    ) -> None:
        self.play_button_tag = f"{tag}{SUF_PLAYER_PLAY}"
        self.pause_button_tag = f"{tag}{SUF_PLAYER_PAUSE}"
        self.stop_button_tag = f"{tag}{SUF_PLAYER_STOP}"
        self.position_text_tag = f"{tag}{SUF_PLAYER_POSITION}"

        self.on_play: Optional[VoidCallback] = None
        self.on_pause_or_resume: Optional[VoidCallback] = None
        self.on_stop: Optional[VoidCallback] = None

        self._layout = layout
        self._lbl_play = language_manager[
            Page.GLOBAL,
            Panel.PLAYER,
            TextType.LABEL,
            PlayerElements.PLAY,
        ]
        self._lbl_pause = language_manager[
            Page.GLOBAL,
            Panel.PLAYER,
            TextType.LABEL,
            PlayerElements.PAUSE,
        ]
        self._lbl_resume = language_manager[
            Page.GLOBAL,
            Panel.PLAYER,
            TextType.LABEL,
            PlayerElements.RESUME,
        ]
        self._lbl_stop = language_manager[
            Page.GLOBAL,
            Panel.PLAYER,
            TextType.LABEL,
            PlayerElements.STOP,
        ]
        self._lbl_position = language_manager[
            Page.GLOBAL,
            Panel.PLAYER,
            TextType.LABEL,
            PlayerElements.POSITION_PREFIX,
        ]
        self._lbl_samples = language_manager[
            Page.GLOBAL,
            Panel.PLAYER,
            TextType.LABEL,
            PlayerElements.SAMPLES_SUFFIX,
        ]
        self._msg_no_audio = language_manager[
            Page.GLOBAL,
            Panel.PLAYER,
            TextType.MESSAGE,
            PlayerElements.NO_AUDIO_LOADED,
        ]

        super().__init__(
            tag=tag,
            parent=parent,
            width=layout.panel.width,
            height=layout.panel.height,
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

        ThemeRegistry.get(TAG_GLOBAL_THEME_PLAYER_TOOLBAR).bind_to_item(self.tag)

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
                    callback=self._on_play_clicked,
                    enabled=False,
                    width=-1,
                )
                GUIButton(
                    tag=self.pause_button_tag,
                    label=self._lbl_pause,
                    callback=self._on_pause_or_resume_clicked,
                    enabled=False,
                    width=-1,
                )
                GUIButton(
                    tag=self.stop_button_tag,
                    label=self._lbl_stop,
                    callback=self._on_stop_clicked,
                    enabled=False,
                    width=-1,
                )

    def update_view(self, view_model: PlayerViewModel) -> None:
        if not view_model.has_audio:
            dpg_configure_item(self.play_button_tag, enabled=False)
            dpg_configure_item(self.pause_button_tag, enabled=False)
            dpg_configure_item(self.stop_button_tag, enabled=False)
            dpg_set_value(self.position_text_tag, self._msg_no_audio)
            return

        dpg_configure_item(self.play_button_tag, enabled=True)
        dpg_configure_item(
            self.pause_button_tag,
            enabled=view_model.is_playing or view_model.is_paused,
        )
        dpg_configure_item(self.stop_button_tag, enabled=True)

        if view_model.is_paused:
            dpg_set_item_label(self.pause_button_tag, self._lbl_resume)
        else:
            dpg_set_item_label(self.pause_button_tag, self._lbl_pause)

        position_text = (
            f"{self._lbl_position}{view_model.current_position}" f"/{view_model.total_samples}{self._lbl_samples}"
        )
        dpg_set_value(self.position_text_tag, position_text)

    def _on_play_clicked(self) -> None:
        self.call(self.on_play)

    def _on_pause_or_resume_clicked(self) -> None:
        self.call(self.on_pause_or_resume)

    def _on_stop_clicked(self) -> None:
        self.call(self.on_stop)
