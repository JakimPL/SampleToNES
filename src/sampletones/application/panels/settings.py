from typing import Dict, List, cast

import dearpygui.dearpygui as dpg

from sampletones.audio import SAMPLE_RATES, AudioDevice, AudioDeviceManager, SampleRate
from sampletones.typehints import Sender

from ..config.settings import AudioSettingsData
from ..constants import (
    DIM_AUDIO_SETTINGS_COMBO_WIDTH,
    DIM_AUDIO_SETTINGS_LABEL_WIDTH,
    DIM_AUDIO_SETTINGS_WINDOW_HEIGHT,
    DIM_AUDIO_SETTINGS_WINDOW_WIDTH,
    LBL_AUDIO_SETTINGS_APPLY,
    LBL_AUDIO_SETTINGS_OUTPUT_DEVICE,
    LBL_AUDIO_SETTINGS_REFRESH_DEVICES,
    LBL_AUDIO_SETTINGS_SAMPLE_RATE,
    LBL_AUDIO_SETTINGS_TITLE,
    SUF_AUDIO_SETTINGS_HZ,
    TAG_AUDIO_SETTINGS_APPLY_BUTTON,
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
from ..utils.dialogs import show_error_dialog
from ..utils.dpg import dpg_configure_item, dpg_set_value


class GUIAudioSettingsWindow(GUIWindow):
    def __init__(self, audio_device_manager: AudioDeviceManager) -> None:
        self.audio_device_manager = audio_device_manager

        self._devices: Dict[int, AudioDevice] = {}
        self._device_name_to_device: Dict[str, AudioDevice] = {}

        self._device_items: List[str] = []
        self._current_device_name: str = ""
        self._current_sample_rate: str = ""

        super().__init__(
            tag=TAG_AUDIO_SETTINGS_WINDOW,
            width=DIM_AUDIO_SETTINGS_WINDOW_WIDTH,
            height=DIM_AUDIO_SETTINGS_WINDOW_HEIGHT,
        )

    def prepare(self) -> None:
        settings_data = AudioSettingsData.from_device_manager(self.audio_device_manager)
        self._devices = dict(settings_data.devices)
        self._device_name_to_device = {device.name: device for device in self._devices.values()}
        self._device_items = [device.name for device in self._devices.values()]

        current_device = settings_data.current_device
        self._current_device_name = current_device.name
        self._current_sample_rate = f"{current_device.sample_rate}{SUF_AUDIO_SETTINGS_HZ}"

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
            dpg.add_separator()
            self._create_action_buttons()

        self._update_combos()

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
        self._update_combos()

    def _update_combos(self) -> None:
        if not self._device_items:
            return

        dpg_configure_item(TAG_AUDIO_SETTINGS_DEVICE_COMBO, items=self._device_items)
        device = self._device_name_to_device.get(self._current_device_name)
        if device is None:
            dpg_set_value(TAG_AUDIO_SETTINGS_DEVICE_COMBO, self._device_items[0] if self._device_items else "")
            device = self._devices[0]
        else:
            dpg_set_value(TAG_AUDIO_SETTINGS_DEVICE_COMBO, self._current_device_name)

        sample_rate_items = [f"{rate}{SUF_AUDIO_SETTINGS_HZ}" for rate in device.supported_sample_rates]

        dpg_configure_item(TAG_AUDIO_SETTINGS_SAMPLE_RATE_COMBO, items=sample_rate_items)

        current_sample_rate_value = dpg.get_value(TAG_AUDIO_SETTINGS_SAMPLE_RATE_COMBO)
        if current_sample_rate_value not in sample_rate_items:
            default_sample_rate = f"{device.default_sample_rate}{SUF_AUDIO_SETTINGS_HZ}"
            if default_sample_rate in sample_rate_items:
                dpg_set_value(TAG_AUDIO_SETTINGS_SAMPLE_RATE_COMBO, default_sample_rate)
            elif sample_rate_items:
                dpg_set_value(TAG_AUDIO_SETTINGS_SAMPLE_RATE_COMBO, sample_rate_items[0])

    def _get_selected_device_index(self) -> int:
        try:
            device = self._device_name_to_device[self._current_device_name]
        except KeyError as exception:
            show_error_dialog(exception, f"Audio device '{self._current_device_name}' not found")
            return -1

        return device.index

    def _get_selected_sample_rate(self) -> SampleRate:
        sample_rate_str: str = dpg.get_value(TAG_AUDIO_SETTINGS_SAMPLE_RATE_COMBO)
        sample_rate: int = int(sample_rate_str.replace(SUF_AUDIO_SETTINGS_HZ, ""))
        assert sample_rate in SAMPLE_RATES
        return cast(SampleRate, sample_rate)

    def _refresh_devices(self) -> None:
        self.audio_device_manager.refresh_devices()
        self.prepare()
        self._update_combos()

    def _apply(self) -> None:
        device_index = self._get_selected_device_index()
        sample_rate = self._get_selected_sample_rate()
        self.audio_device_manager.configure_device(device_index, sample_rate)
        self.hide()
