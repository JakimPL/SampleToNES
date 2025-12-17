from typing import Dict, List, Optional, Tuple, Union, cast

import dearpygui.dearpygui as dpg

from sampletones.audio import (
    SAMPLE_RATES,
    AudioDevice,
    AudioDeviceManager,
    CurrentDevice,
    SampleRate,
)
from sampletones.typehints import Sender

from ..config.settings import AudioSettingsData
from ..constants.general import TTL_WINDOW_MAIN, VAL_SEPARATOR_DEVICE_LABEL_INDEX_NAME
from ..constants.settings import (
    DIM_COMBO_WIDTH_SETTINGS_AUDIO,
    DIM_TEXT_WIDTH_SETTINGS_AUDIO,
    DIM_WINDOW_HEIGHT_SETTINGS_AUDIO,
    DIM_WINDOW_WIDTH_SETTINGS_AUDIO,
    LBL_BUTTON_SETTINGS_AUDIO_APPLY,
    LBL_BUTTON_SETTINGS_AUDIO_REFRESH_DEVICES,
    LBL_TEXT_SETTINGS_AUDIO_OUTPUT_DEVICE,
    LBL_TEXT_SETTINGS_AUDIO_SAMPLE_RATE,
    SUF_SETTINGS_AUDIO_HZ,
    TAG_BUTTON_SETTINGS_AUDIO_APPLY,
    TAG_BUTTON_SETTINGS_AUDIO_REFRESH,
    TAG_COMBO_SETTINGS_AUDIO_DEVICE,
    TAG_COMBO_SETTINGS_AUDIO_SAMPLE_RATE,
    TAG_GROUP_SETTINGS_AUDIO_DEVICE,
    TAG_GROUP_SETTINGS_AUDIO_SAMPLE_RATE,
    TAG_WINDOW_SETTINGS_AUDIO,
    TTL_SETTINGS_AUDIO,
)
from ..elements.button import GUIButton
from ..elements.window import GUIWindow
from ..utils.align import table_wrapper
from ..utils.dpg import dpg_configure_item, dpg_set_value


class GUIAudioSettingsWindow(GUIWindow):
    def __init__(self, audio_device_manager: AudioDeviceManager) -> None:
        self.audio_device_manager = audio_device_manager

        self._devices: Dict[int, AudioDevice] = {}
        self._current_device: Optional[CurrentDevice] = None
        self._device_items: List[str] = []
        self._current_device_index: int = -1
        self._current_device_name: str = ""
        self._current_sample_rate: str = ""

        super().__init__(
            tag=TAG_WINDOW_SETTINGS_AUDIO,
            parent=TTL_WINDOW_MAIN,
            width=DIM_WINDOW_WIDTH_SETTINGS_AUDIO,
            height=DIM_WINDOW_HEIGHT_SETTINGS_AUDIO,
        )

    def prepare(self) -> None:
        settings_data = AudioSettingsData.from_device_manager(self.audio_device_manager)
        self._devices = dict(settings_data.devices)
        self._device_items = list(map(self._get_device_label, self._devices.values()))

        self._current_device = settings_data.current_device
        self._set_device_index_name_and_sample_rate(self._current_device)

    def create_panel(self) -> None:
        with dpg.window(
            tag=self.tag,
            label=TTL_SETTINGS_AUDIO,
            width=self.width,
            height=self.height,
            no_resize=True,
            no_collapse=True,
            on_close=self.hide,
            modal=True,
        ):
            self._create_device_selection()
            self._create_sample_rate_selection()
            dpg.add_separator()
            self._create_action_buttons()

        self._update_combos()

    def _get_device_label(self, device: Optional[Union[CurrentDevice, AudioDevice]]) -> str:
        if device is None:
            return ""

        device_index = device.index if isinstance(device, AudioDevice) else device.device_index
        return self._get_device_label_from_index_name(device_index, device.name)

    def _get_device_label_from_index_name(self, device_index: int, device_name: str) -> str:
        return f"{device_index}{VAL_SEPARATOR_DEVICE_LABEL_INDEX_NAME}{device_name}"

    def _retrieve_device_index_and_name(self, device_label: str) -> Tuple[int, str]:
        separator = VAL_SEPARATOR_DEVICE_LABEL_INDEX_NAME
        index = device_label.find(separator)
        if index == -1:
            raise ValueError(f"Invalid device label format: {device_label}")

        device_index = device_label[:index]
        device_name = device_label[index + len(separator) :]
        return int(device_index), device_name

    def _create_device_selection(self) -> None:
        with dpg.group(tag=TAG_GROUP_SETTINGS_AUDIO_DEVICE, horizontal=True):
            dpg.add_text(LBL_TEXT_SETTINGS_AUDIO_OUTPUT_DEVICE)
            dpg.add_spacer(
                width=DIM_TEXT_WIDTH_SETTINGS_AUDIO - int(dpg.get_text_size(LBL_TEXT_SETTINGS_AUDIO_OUTPUT_DEVICE)[0])
            )
            dpg.add_combo(
                tag=TAG_COMBO_SETTINGS_AUDIO_DEVICE,
                items=self._device_items,
                default_value=self._get_device_label(self._current_device),
                width=DIM_COMBO_WIDTH_SETTINGS_AUDIO,
                callback=self._on_device_changed,
            )

    def _create_sample_rate_selection(self) -> None:
        with dpg.group(tag=TAG_GROUP_SETTINGS_AUDIO_SAMPLE_RATE, horizontal=True):
            dpg.add_text(LBL_TEXT_SETTINGS_AUDIO_SAMPLE_RATE)
            dpg.add_spacer(
                width=DIM_TEXT_WIDTH_SETTINGS_AUDIO - int(dpg.get_text_size(LBL_TEXT_SETTINGS_AUDIO_SAMPLE_RATE)[0])
            )
            dpg.add_combo(
                tag=TAG_COMBO_SETTINGS_AUDIO_SAMPLE_RATE,
                items=[],
                default_value=self._current_sample_rate,
                width=DIM_COMBO_WIDTH_SETTINGS_AUDIO,
            )

    @table_wrapper(columns=2)
    def _create_action_buttons(self) -> None:
        GUIButton(
            tag=TAG_BUTTON_SETTINGS_AUDIO_REFRESH,
            label=LBL_BUTTON_SETTINGS_AUDIO_REFRESH_DEVICES,
            callback=self._refresh_devices,
            width=-1,
        )
        GUIButton(
            tag=TAG_BUTTON_SETTINGS_AUDIO_APPLY,
            label=LBL_BUTTON_SETTINGS_AUDIO_APPLY,
            callback=self._apply,
            width=-1,
        )

    def _on_device_changed(self, sender: Sender, app_data: str) -> None:
        self._current_device_index, self._current_device_name = self._retrieve_device_index_and_name(app_data)
        self._update_combos()

    def _update_combos(self) -> None:
        if not self._device_items:
            return

        dpg_configure_item(TAG_COMBO_SETTINGS_AUDIO_DEVICE, items=self._device_items)
        if self._current_device is None or not self._devices:
            dpg_set_value(TAG_COMBO_SETTINGS_AUDIO_DEVICE, "")
            return

        device_label = self._get_device_label_from_index_name(self._current_device_index, self._current_device_name)
        device = self._devices[self._current_device_index]
        sample_rate_items = [f"{rate}{SUF_SETTINGS_AUDIO_HZ}" for rate in device.supported_sample_rates]
        dpg_set_value(TAG_COMBO_SETTINGS_AUDIO_DEVICE, device_label)
        dpg_configure_item(TAG_COMBO_SETTINGS_AUDIO_SAMPLE_RATE, items=sample_rate_items)

        current_sample_rate_value = dpg.get_value(TAG_COMBO_SETTINGS_AUDIO_SAMPLE_RATE)
        if current_sample_rate_value not in sample_rate_items:
            default_sample_rate = f"{device.default_sample_rate}{SUF_SETTINGS_AUDIO_HZ}"
            if default_sample_rate in sample_rate_items:
                dpg_set_value(TAG_COMBO_SETTINGS_AUDIO_SAMPLE_RATE, default_sample_rate)
            elif sample_rate_items:
                dpg_set_value(TAG_COMBO_SETTINGS_AUDIO_SAMPLE_RATE, sample_rate_items[0])

    def _get_selected_device_index(self) -> int:
        return self._retrieve_device_index_and_name(dpg.get_value(TAG_COMBO_SETTINGS_AUDIO_DEVICE))[0]

    def _get_selected_sample_rate(self) -> SampleRate:
        sample_rate_string: str = dpg.get_value(TAG_COMBO_SETTINGS_AUDIO_SAMPLE_RATE)
        sample_rate: int = int(sample_rate_string.replace(SUF_SETTINGS_AUDIO_HZ, ""))
        assert sample_rate in SAMPLE_RATES, "Unsupported sample rate selected"
        return cast(SampleRate, sample_rate)

    def _refresh_devices(self) -> None:
        self.audio_device_manager.refresh_devices()
        self.prepare()
        self._update_combos()

    def _set_device_index_name_and_sample_rate(self, current_device: CurrentDevice) -> None:
        self._current_device_index = current_device.device_index
        self._current_device_name = current_device.name
        self._current_sample_rate = f"{current_device.sample_rate}{SUF_SETTINGS_AUDIO_HZ}"

    def _apply(self) -> None:
        device_index = self._get_selected_device_index()
        sample_rate = self._get_selected_sample_rate()
        self.audio_device_manager.configure_device(device_index, sample_rate)

        self._current_device = self.audio_device_manager.get_current_device()
        self._set_device_index_name_and_sample_rate(self._current_device)
        self.hide()
