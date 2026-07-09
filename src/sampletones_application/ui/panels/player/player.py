from typing import Optional

import dearpygui.dearpygui as dpg

from sampletones_application.categories.elements.global_ import PlayerElements
from sampletones_application.categories.hierarchy import Page, Panel, TextType
from sampletones_application.categories.manager import LanguageManager
from sampletones_application.constants.general import TAG_GLOBAL_THEME_PLAYER_TOOLBAR
from sampletones_application.constants.player import (
    SUF_PLAYER_CARD,
    SUF_PLAYER_PAUSE,
    SUF_PLAYER_PLAY,
    SUF_PLAYER_POSITION,
    SUF_PLAYER_STOP,
    SUF_PLAYER_TOOLTIP,
)
from sampletones_application.layout.player import PlayerLayout
from sampletones_application.ui.elements.fonts.font import Font
from sampletones_application.ui.elements.fonts.registry import FontRegistry
from sampletones_application.ui.elements.panel import GUIPanel
from sampletones_application.ui.panels.player.controls import (
    centered_card,
    create_transport_controls,
)
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
        *,
        layout: PlayerLayout,
        language_manager: LanguageManager,
    ) -> None:
        self.card_tag = f"{tag}{SUF_PLAYER_CARD}"
        self.play_button_tag = f"{tag}{SUF_PLAYER_PLAY}"
        self.pause_button_tag = f"{tag}{SUF_PLAYER_PAUSE}"
        self.stop_button_tag = f"{tag}{SUF_PLAYER_STOP}"
        self.position_text_tag = f"{tag}{SUF_PLAYER_POSITION}"
        self.pause_tooltip_tag = f"{self.pause_button_tag}{SUF_PLAYER_TOOLTIP}"

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

        super().__init__(tag=tag)

    def create_panel(self, parent: str) -> None:
        with centered_card(parent, self.tag, self.card_tag, self._layout.card.width):
            self._create_controls()
            dpg.add_text(self._msg_no_audio, tag=self.position_text_tag)
            FontRegistry.bind_to_item(self.position_text_tag, Font.REGULAR_SMALL)

        ThemeRegistry.get(TAG_GLOBAL_THEME_PLAYER_TOOLBAR).bind_to_item(self.card_tag)

    def _create_controls(self) -> None:
        create_transport_controls(
            self.card_tag,
            layout=self._layout,
            glyphs=self._glyphs.player,
            play_tag=self.play_button_tag,
            pause_tag=self.pause_button_tag,
            stop_tag=self.stop_button_tag,
            play_tooltip=self._lbl_play,
            pause_tooltip=self._lbl_pause,
            stop_tooltip=self._lbl_stop,
            on_play=self._on_play_clicked,
            on_pause_or_resume=self._on_pause_or_resume_clicked,
            on_stop=self._on_stop_clicked,
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
            dpg_set_item_label(self.pause_button_tag, self._glyphs.player.play)
            dpg_set_value(self.pause_tooltip_tag, self._lbl_resume)
        else:
            dpg_set_item_label(self.pause_button_tag, self._glyphs.player.pause)
            dpg_set_value(self.pause_tooltip_tag, self._lbl_pause)

        position_text = self._get_position_text(view_model)
        dpg_set_value(self.position_text_tag, position_text)

    def _get_position_text(self, view_model: PlayerViewModel) -> str:
        position = f"{self._lbl_position}{view_model.current_position}"
        total = f"{view_model.total_samples}{self._lbl_samples}"
        return f"{position}/{total}"

    def _on_play_clicked(self) -> None:
        self.call(self.on_play)

    def _on_pause_or_resume_clicked(self) -> None:
        self.call(self.on_pause_or_resume)

    def _on_stop_clicked(self) -> None:
        self.call(self.on_stop)
