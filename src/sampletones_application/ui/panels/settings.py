from typing import Any, Callable, Dict, List, Optional, Tuple, Union, cast

import dearpygui.dearpygui as dpg

from sampletones_application.categories.elements.global_ import GlobalDialogTitleElements
from sampletones_application.categories.elements.settings import AudioSettingsElements
from sampletones_application.categories.hierarchy import Page, Panel, TextType
from sampletones_application.categories.manager import LanguageManager
from sampletones_application.constants.general import TAG_GLOBAL_THEME_DIALOG
from sampletones_application.constants.settings import (
    FMT_SETTINGS_AUDIO_HZ,
    TAG_SETTINGS_AUDIO_BUTTON_APPLY,
    TAG_SETTINGS_AUDIO_BUTTON_REFRESH,
    TAG_SETTINGS_AUDIO_COMBO_BUFFER_SIZE,
    TAG_SETTINGS_AUDIO_COMBO_DEVICE,
    TAG_SETTINGS_AUDIO_COMBO_SAMPLE_RATE,
    TAG_SETTINGS_AUDIO_GROUP_BUFFER_SIZE,
    TAG_SETTINGS_AUDIO_GROUP_DEVICE,
    TAG_SETTINGS_AUDIO_GROUP_SAMPLE_RATE,
    TAG_SETTINGS_AUDIO_WINDOW,
)
from sampletones_application.layout.settings import SettingsLayout
from sampletones_application.ui.elements.button import GUIButton
from sampletones_application.ui.elements.fonts.font import Font
from sampletones_application.ui.elements.fonts.registry import FontRegistry
from sampletones_application.ui.elements.window import GUIWindow
from sampletones_application.ui.themes.registry import ThemeRegistry
from sampletones_application.utils.gui.align import table_wrapper
from sampletones_application.utils.gui.dpg import dpg_configure_item, dpg_set_value
from sampletones_application.view_model.shared.audio_settings import AudioSettingsViewModel
from sampletones_core.audio import (
    AudioDevice,
    CurrentDevice,
    validate_sample_rate,
)
from sampletones_core.constants.audio import (
    BUFFER_SIZES,
    BufferSize,
    SampleRate,
)
from sampletones_shared.types.application import Sender
from sampletones_shared.types.callback import VoidCallback


class GUIAudioSettingsWindow(GUIWindow):
    def __init__(
        self,
        *,
        layout: SettingsLayout,
        language_manager: LanguageManager,
    ) -> None:
        self._layout = layout
        self._dialog_theme = ThemeRegistry.get(TAG_GLOBAL_THEME_DIALOG)

        self.on_commit: Optional[Callable[[int, SampleRate, BufferSize], None]] = None
        self.on_refresh_devices: Optional[VoidCallback] = None

        self._devices: Dict[int, AudioDevice] = {}
        self._current_device: Optional[CurrentDevice] = None
        self._device_items: List[str] = []
        self._current_device_index: int = -1
        self._current_device_name: str = ""
        self._current_sample_rate: str = ""
        self._current_buffer_size: str = ""

        self._ttl_main_window = language_manager[
            Page.GLOBAL,
            Panel.DIALOG,
            TextType.TITLE,
            GlobalDialogTitleElements.MAIN_WINDOW,
        ]
        self._ttl_audio = language_manager[
            Page.SETTINGS,
            Panel.AUDIO,
            TextType.TITLE,
            AudioSettingsElements.WINDOW_TITLE,
        ]
        self._lbl_output_device = language_manager[
            Page.SETTINGS,
            Panel.AUDIO,
            TextType.LABEL,
            AudioSettingsElements.OUTPUT_DEVICE,
        ]
        self._lbl_sample_rate = language_manager[
            Page.SETTINGS,
            Panel.AUDIO,
            TextType.LABEL,
            AudioSettingsElements.SAMPLE_RATE,
        ]
        self._lbl_buffer_size = language_manager[
            Page.SETTINGS,
            Panel.AUDIO,
            TextType.LABEL,
            AudioSettingsElements.BUFFER_SIZE,
        ]
        self._lbl_apply_button = language_manager[
            Page.SETTINGS,
            Panel.AUDIO,
            TextType.LABEL,
            AudioSettingsElements.APPLY_BUTTON,
        ]
        self._lbl_refresh_button = language_manager[
            Page.SETTINGS,
            Panel.AUDIO,
            TextType.LABEL,
            AudioSettingsElements.REFRESH_DEVICES_BUTTON,
        ]

        super().__init__(
            tag=TAG_SETTINGS_AUDIO_WINDOW,
            parent=self._ttl_main_window,
            width=layout.window.width,
            height=layout.window.height,
        )

    def open(self, view_model: AudioSettingsViewModel) -> None:
        """Shows the window seeded with the given audio settings."""
        self._seed(view_model)
        self.show()

    def prepare(self, *_args: Any, **_kwargs: Any) -> None:
        """The rendered values are seeded by :meth:`open` before the tree rebuilds."""

    def update_view(self, view_model: AudioSettingsViewModel) -> None:
        """Re-seeds the values and repaints the combos of the open window."""
        self._seed(view_model)
        self._update_combos()

    def _seed(self, view_model: AudioSettingsViewModel) -> None:
        self._devices = dict(view_model.devices)
        self._device_items = list(
            map(self._get_device_label, self._devices.values()),
        )

        self._current_device = view_model.current_device
        self._set_device_index_name_and_sample_rate(view_model.current_device)
        self._current_buffer_size = str(view_model.buffer_size)

    def create_panel(self) -> None:
        with dpg.window(
            tag=self.tag,
            label=self._ttl_audio,
            width=self.width,
            height=self.height,
            no_resize=True,
            no_collapse=True,
            on_close=self.hide,
            modal=True,
        ):
            self._create_device_selection()
            self._create_sample_rate_selection()
            self._create_buffer_size_selection()
            dpg.add_separator()
            self._create_action_buttons()

        for combo_tag in (
            TAG_SETTINGS_AUDIO_COMBO_DEVICE,
            TAG_SETTINGS_AUDIO_COMBO_SAMPLE_RATE,
            TAG_SETTINGS_AUDIO_COMBO_BUFFER_SIZE,
        ):
            self._dialog_theme.bind_to_item(combo_tag)
        self._update_combos()

    def _get_device_label(
        self,
        device: Optional[Union[CurrentDevice, AudioDevice]],
    ) -> str:
        if device is None:
            return ""

        device_index = device.index if isinstance(device, AudioDevice) else device.device_index
        return self._get_device_label_from_index_name(device_index, device.name)

    def _get_device_label_from_index_name(self, device_index: int, device_name: str) -> str:
        return f"{device_index}{': '}{device_name}"

    def _retrieve_device_index_and_name(self, device_label: str) -> Tuple[int, str]:
        separator = ": "
        index = device_label.find(separator)
        if index == -1:
            raise ValueError(f"Invalid device label format: {device_label}")

        device_index = device_label[:index]
        device_name = device_label[index + len(separator) :]
        return int(device_index), device_name

    def _create_device_selection(self) -> None:
        with dpg.group(tag=TAG_SETTINGS_AUDIO_GROUP_DEVICE, horizontal=True):
            label_id = dpg.add_text(self._lbl_output_device)
            FontRegistry.bind_to_item(label_id, Font.BOLD)
            dpg.add_spacer(
                width=self._layout.label_width - int(dpg.get_text_size(self._lbl_output_device)[0]),
            )
            dpg.add_combo(
                tag=TAG_SETTINGS_AUDIO_COMBO_DEVICE,
                items=self._device_items,
                default_value=self._get_device_label(self._current_device),
                width=self._layout.combo_width,
                callback=self._on_device_changed,
            )

    def _create_sample_rate_selection(self) -> None:
        with dpg.group(tag=TAG_SETTINGS_AUDIO_GROUP_SAMPLE_RATE, horizontal=True):
            label_id = dpg.add_text(self._lbl_sample_rate)
            FontRegistry.bind_to_item(label_id, Font.BOLD)
            dpg.add_spacer(
                width=self._layout.label_width - int(dpg.get_text_size(self._lbl_sample_rate)[0]),
            )
            dpg.add_combo(
                tag=TAG_SETTINGS_AUDIO_COMBO_SAMPLE_RATE,
                items=[],
                default_value=self._current_sample_rate,
                width=self._layout.combo_width,
            )

    def _create_buffer_size_selection(self) -> None:
        with dpg.group(tag=TAG_SETTINGS_AUDIO_GROUP_BUFFER_SIZE, horizontal=True):
            label_id = dpg.add_text(self._lbl_buffer_size)
            FontRegistry.bind_to_item(label_id, Font.BOLD)
            dpg.add_spacer(
                width=self._layout.label_width - int(dpg.get_text_size(self._lbl_buffer_size)[0]),
            )
            dpg.add_combo(
                tag=TAG_SETTINGS_AUDIO_COMBO_BUFFER_SIZE,
                items=[str(size) for size in BUFFER_SIZES],
                default_value=self._current_buffer_size,
                width=self._layout.combo_width,
            )

    @table_wrapper(columns=2)
    def _create_action_buttons(self) -> None:
        GUIButton(
            tag=TAG_SETTINGS_AUDIO_BUTTON_REFRESH,
            label=self._lbl_refresh_button,
            callback=self._refresh_devices,
            width=-1,
        )
        GUIButton(
            tag=TAG_SETTINGS_AUDIO_BUTTON_APPLY,
            label=self._lbl_apply_button,
            callback=self._commit,
            width=-1,
        )

    def _on_device_changed(self, sender: Sender, app_data: str) -> None:
        self._current_device_index, self._current_device_name = self._retrieve_device_index_and_name(app_data)
        self._update_combos()

    def _update_combos(self) -> None:
        if not self._device_items:
            return

        dpg_configure_item(TAG_SETTINGS_AUDIO_COMBO_DEVICE, items=self._device_items)
        if self._current_device is None or not self._devices:
            dpg_set_value(TAG_SETTINGS_AUDIO_COMBO_DEVICE, "")
            return

        device_label = self._get_device_label_from_index_name(
            self._current_device_index,
            self._current_device_name,
        )
        device = self._devices[self._current_device_index]
        sample_rate_items = [f"{rate}{FMT_SETTINGS_AUDIO_HZ}" for rate in device.supported_sample_rates]
        dpg_set_value(TAG_SETTINGS_AUDIO_COMBO_DEVICE, device_label)
        dpg_configure_item(
            TAG_SETTINGS_AUDIO_COMBO_SAMPLE_RATE,
            items=sample_rate_items,
        )

        current_sample_rate_value = dpg.get_value(TAG_SETTINGS_AUDIO_COMBO_SAMPLE_RATE)
        if current_sample_rate_value not in sample_rate_items:
            default_sample_rate = f"{device.default_sample_rate}{FMT_SETTINGS_AUDIO_HZ}"
            if default_sample_rate in sample_rate_items:
                dpg_set_value(
                    TAG_SETTINGS_AUDIO_COMBO_SAMPLE_RATE,
                    default_sample_rate,
                )
            elif sample_rate_items:
                dpg_set_value(
                    TAG_SETTINGS_AUDIO_COMBO_SAMPLE_RATE,
                    sample_rate_items[0],
                )

    def _get_selected_device_index(self) -> int:
        return self._retrieve_device_index_and_name(dpg.get_value(TAG_SETTINGS_AUDIO_COMBO_DEVICE))[0]

    def _get_selected_sample_rate(self) -> SampleRate:
        sample_rate_string: str = dpg.get_value(TAG_SETTINGS_AUDIO_COMBO_SAMPLE_RATE)
        sample_rate: int = int(sample_rate_string.replace(FMT_SETTINGS_AUDIO_HZ, ""))
        validate_sample_rate(sample_rate)
        return cast(SampleRate, sample_rate)

    def _get_selected_buffer_size(self) -> BufferSize:
        buffer_size_string: str = dpg.get_value(TAG_SETTINGS_AUDIO_COMBO_BUFFER_SIZE)
        buffier_size: int = int(buffer_size_string)
        assert buffier_size in BUFFER_SIZES, "Unsupported buffer size selected"
        return buffier_size

    def _refresh_devices(self) -> None:
        self.call(self.on_refresh_devices)

    def _set_device_index_name_and_sample_rate(self, current_device: CurrentDevice) -> None:
        self._current_device_index = current_device.device_index
        self._current_device_name = current_device.name
        self._current_sample_rate = f"{current_device.sample_rate}{FMT_SETTINGS_AUDIO_HZ}"

    def _commit(self) -> None:
        self.call(
            self.on_commit,
            self._get_selected_device_index(),
            self._get_selected_sample_rate(),
            self._get_selected_buffer_size(),
        )
        self.hide()
