from typing import List, Optional

import dearpygui.dearpygui as dpg

from ..config.settings import AudioSettingsData
from ..constants import (
    DIM_AUDIO_SETTINGS_COMBO_WIDTH,
    DIM_AUDIO_SETTINGS_LABEL_WIDTH,
    DIM_AUDIO_SETTINGS_WINDOW_HEIGHT,
    DIM_AUDIO_SETTINGS_WINDOW_WIDTH,
    LBL_AUDIO_SETTINGS_APPLY,
    LBL_AUDIO_SETTINGS_BIT_DEPTH,
    LBL_AUDIO_SETTINGS_OUTPUT_DEVICE,
    LBL_AUDIO_SETTINGS_REFRESH_DEVICES,
    LBL_AUDIO_SETTINGS_SAMPLE_RATE,
    LBL_AUDIO_SETTINGS_TITLE,
    SUF_AUDIO_SETTINGS_BIT,
    SUF_AUDIO_SETTINGS_HZ,
    TAG_AUDIO_SETTINGS_APPLY_BUTTON,
    TAG_AUDIO_SETTINGS_BIT_DEPTH_COMBO,
    TAG_AUDIO_SETTINGS_BIT_DEPTH_GROUP,
    TAG_AUDIO_SETTINGS_DEVICE_COMBO,
    TAG_AUDIO_SETTINGS_DEVICE_GROUP,
    TAG_AUDIO_SETTINGS_REFRESH_BUTTON,
    TAG_AUDIO_SETTINGS_SAMPLE_RATE_COMBO,
    TAG_AUDIO_SETTINGS_SAMPLE_RATE_GROUP,
    TAG_AUDIO_SETTINGS_WINDOW,
)
from ..elements.button import GUIButton
from ..elements.window import GUIWindow
from ..utils.dpg import dpg_delete_item


class GUIAudioSettingsWindow(GUIWindow):
    def __init__(self, parent: Optional[str] = None) -> None:
        self._sample_rate_items: List[str] = []
        self._bit_depth_items: List[str] = []
        self._device_items: List[str] = []
        self._current_device_name: str = ""
        self._current_sample_rate: str = ""
        self._current_bit_depth: str = ""

        super().__init__(
            tag=TAG_AUDIO_SETTINGS_WINDOW,
            parent=parent,
            width=DIM_AUDIO_SETTINGS_WINDOW_WIDTH,
            height=DIM_AUDIO_SETTINGS_WINDOW_HEIGHT,
        )

    def prepare(self, settings_data: AudioSettingsData) -> None:
        self._device_items = settings_data.device_names
        self._current_device_name = settings_data.current_device_name

        self._sample_rate_items = [f"{rate}{SUF_AUDIO_SETTINGS_HZ}" for rate in settings_data.sample_rates]
        self._current_sample_rate = f"{settings_data.current_sample_rate}{SUF_AUDIO_SETTINGS_HZ}"

        self._bit_depth_items = [f"{depth}{SUF_AUDIO_SETTINGS_BIT}" for depth in settings_data.bit_depths]
        self._current_bit_depth = f"{settings_data.current_bit_depth}{SUF_AUDIO_SETTINGS_BIT}"

    def create_panel(self) -> None:
        with dpg.window(
            tag=self.tag,
            label=LBL_AUDIO_SETTINGS_TITLE,
            width=self.width,
            height=self.height,
            no_resize=True,
            no_collapse=True,
            on_close=self.hide,
        ):
            self._create_device_selection()
            self._create_sample_rate_selection()
            self._create_bit_depth_selection()
            dpg.add_separator()
            self._create_action_buttons()

    def _create_device_selection(self) -> None:
        with dpg.group(tag=TAG_AUDIO_SETTINGS_DEVICE_GROUP, horizontal=True):
            dpg.add_text(LBL_AUDIO_SETTINGS_OUTPUT_DEVICE)
            dpg.add_spacer(
                width=DIM_AUDIO_SETTINGS_LABEL_WIDTH - int(dpg.get_text_size(LBL_AUDIO_SETTINGS_OUTPUT_DEVICE)[0])
            )
            dpg.add_combo(
                tag=TAG_AUDIO_SETTINGS_DEVICE_COMBO,
                items=self._device_items,
                default_value=self._current_device_name,
                width=DIM_AUDIO_SETTINGS_COMBO_WIDTH,
            )

    def _create_sample_rate_selection(self) -> None:
        with dpg.group(tag=TAG_AUDIO_SETTINGS_SAMPLE_RATE_GROUP, horizontal=True):
            dpg.add_text(LBL_AUDIO_SETTINGS_SAMPLE_RATE)
            dpg.add_spacer(
                width=DIM_AUDIO_SETTINGS_LABEL_WIDTH - int(dpg.get_text_size(LBL_AUDIO_SETTINGS_SAMPLE_RATE)[0])
            )
            dpg.add_combo(
                tag=TAG_AUDIO_SETTINGS_SAMPLE_RATE_COMBO,
                items=self._sample_rate_items,
                default_value=self._current_sample_rate,
                width=DIM_AUDIO_SETTINGS_COMBO_WIDTH,
            )

    def _create_bit_depth_selection(self) -> None:
        with dpg.group(tag=TAG_AUDIO_SETTINGS_BIT_DEPTH_GROUP, horizontal=True):
            dpg.add_text(LBL_AUDIO_SETTINGS_BIT_DEPTH)
            dpg.add_spacer(
                width=DIM_AUDIO_SETTINGS_LABEL_WIDTH - int(dpg.get_text_size(LBL_AUDIO_SETTINGS_BIT_DEPTH)[0])
            )
            dpg.add_combo(
                tag=TAG_AUDIO_SETTINGS_BIT_DEPTH_COMBO,
                items=self._bit_depth_items,
                default_value=self._current_bit_depth,
                width=DIM_AUDIO_SETTINGS_COMBO_WIDTH,
            )

    def _create_action_buttons(self) -> None:
        with dpg.group(horizontal=True):
            GUIButton(
                tag=TAG_AUDIO_SETTINGS_REFRESH_BUTTON,
                label=LBL_AUDIO_SETTINGS_REFRESH_DEVICES,
                callback=self._on_refresh_devices_clicked,
            )
            GUIButton(
                tag=TAG_AUDIO_SETTINGS_APPLY_BUTTON,
                label=LBL_AUDIO_SETTINGS_APPLY,
                callback=self._on_apply_clicked,
            )

    def _on_refresh_devices_clicked(self) -> None:
        pass

    def _on_apply_clicked(self) -> None:
        pass

    def hide(self) -> None:
        dpg_delete_item(TAG_AUDIO_SETTINGS_REFRESH_BUTTON, children_only=False, from_registry=True)
        dpg_delete_item(TAG_AUDIO_SETTINGS_APPLY_BUTTON, children_only=False, from_registry=True)
        dpg_delete_item(self.tag)
