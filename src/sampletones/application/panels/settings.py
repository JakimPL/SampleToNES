from typing import Dict, List

import dearpygui.dearpygui as dpg

from sampletones.audio import AudioDevice, AudioDeviceManager
from sampletones.typehints import Sender

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
from ..utils.align import table_wrapper
from ..utils.dpg import dpg_configure_item, dpg_set_value


class GUIAudioSettingsWindow(GUIWindow):
    def __init__(self, audio_device_manager: AudioDeviceManager) -> None:
        self.audio_device_manager = audio_device_manager

        self._devices: Dict[int, AudioDevice] = {}
        self._device_name_to_device: Dict[str, AudioDevice] = {}

        self._device_items: List[str] = []
        self._current_device_name: str = ""
        self._current_sample_rate: str = ""
        self._current_bit_depth: str = ""

        super().__init__(
            tag=TAG_AUDIO_SETTINGS_WINDOW,
            width=DIM_AUDIO_SETTINGS_WINDOW_WIDTH,
            height=DIM_AUDIO_SETTINGS_WINDOW_HEIGHT,
        )

    def prepare(self) -> None:
        self.audio_device_manager.refresh_devices()
        settings_data = AudioSettingsData.from_device_manager(self.audio_device_manager)
        self._devices = dict(settings_data.devices)
        self._device_name_to_device = {device.name: device for device in self._devices.values()}
        self._device_items = [device.name for device in self._devices.values()]

        current_device = settings_data.get_current_device()
        self._current_device_name = current_device.name
        self._current_sample_rate = f"{settings_data.sample_rate}{SUF_AUDIO_SETTINGS_HZ}"
        self._current_bit_depth = f"{settings_data.bit_depth}{SUF_AUDIO_SETTINGS_BIT}"

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

        self._update_device_dependent_combos()

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
                callback=self._on_device_changed,
            )

    def _create_sample_rate_selection(self) -> None:
        with dpg.group(tag=TAG_AUDIO_SETTINGS_SAMPLE_RATE_GROUP, horizontal=True):
            dpg.add_text(LBL_AUDIO_SETTINGS_SAMPLE_RATE)
            dpg.add_spacer(
                width=DIM_AUDIO_SETTINGS_LABEL_WIDTH - int(dpg.get_text_size(LBL_AUDIO_SETTINGS_SAMPLE_RATE)[0])
            )
            dpg.add_combo(
                tag=TAG_AUDIO_SETTINGS_SAMPLE_RATE_COMBO,
                items=[],
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
                items=[],
                default_value=self._current_bit_depth,
                width=DIM_AUDIO_SETTINGS_COMBO_WIDTH,
            )

    @table_wrapper(columns=2)
    def _create_action_buttons(self) -> None:
        GUIButton(
            tag=TAG_AUDIO_SETTINGS_REFRESH_BUTTON,
            label=LBL_AUDIO_SETTINGS_REFRESH_DEVICES,
            callback=self._refresh_devices,
            width=-1,
        )
        GUIButton(
            tag=TAG_AUDIO_SETTINGS_APPLY_BUTTON,
            label=LBL_AUDIO_SETTINGS_APPLY,
            callback=self._apply,
            width=-1,
        )

    def _on_device_changed(self, sender: Sender, device_name: str) -> None:
        self._current_device_name = device_name
        self._update_device_dependent_combos()

    def _update_device_dependent_combos(self) -> None:
        device = self._device_name_to_device.get(self._current_device_name)
        if device is None:
            return

        sample_rate_items = [f"{rate}{SUF_AUDIO_SETTINGS_HZ}" for rate in device.supported_sample_rates]
        bit_depth_items = [f"{depth}{SUF_AUDIO_SETTINGS_BIT}" for depth in device.supported_bit_depths]

        dpg_configure_item(TAG_AUDIO_SETTINGS_SAMPLE_RATE_COMBO, items=sample_rate_items)
        dpg_configure_item(TAG_AUDIO_SETTINGS_BIT_DEPTH_COMBO, items=bit_depth_items)

        current_sample_rate_value = dpg.get_value(TAG_AUDIO_SETTINGS_SAMPLE_RATE_COMBO)
        if current_sample_rate_value not in sample_rate_items:
            default_sample_rate = f"{device.default_sample_rate}{SUF_AUDIO_SETTINGS_HZ}"
            if default_sample_rate in sample_rate_items:
                dpg_set_value(TAG_AUDIO_SETTINGS_SAMPLE_RATE_COMBO, default_sample_rate)
            elif sample_rate_items:
                dpg_set_value(TAG_AUDIO_SETTINGS_SAMPLE_RATE_COMBO, sample_rate_items[0])

        current_bit_depth_value = dpg.get_value(TAG_AUDIO_SETTINGS_BIT_DEPTH_COMBO)
        if current_bit_depth_value not in bit_depth_items and bit_depth_items:
            dpg_set_value(TAG_AUDIO_SETTINGS_BIT_DEPTH_COMBO, bit_depth_items[0])

    def _get_selected_device_index(self) -> int:
        device = self._device_name_to_device.get(self._current_device_name)
        if device is None:
            raise ValueError(f"Device '{self._current_device_name}' not found")

        return device.index

    def _get_selected_sample_rate(self) -> int:
        sample_rate_str: str = dpg.get_value(TAG_AUDIO_SETTINGS_SAMPLE_RATE_COMBO)
        return int(sample_rate_str.replace(SUF_AUDIO_SETTINGS_HZ, ""))

    def _get_selected_bit_depth(self) -> int:
        bit_depth_str: str = dpg.get_value(TAG_AUDIO_SETTINGS_BIT_DEPTH_COMBO)
        return int(bit_depth_str.replace(SUF_AUDIO_SETTINGS_BIT, ""))

    def _refresh_devices(self) -> None:
        self.prepare()

    def _apply(self) -> None:
        device_index = self._get_selected_device_index()
        sample_rate = self._get_selected_sample_rate()
        bit_depth = self._get_selected_bit_depth()
        self.audio_device_manager.configure_device(device_index, sample_rate, bit_depth)
        self.hide()
