from typing import Any, Callable, Dict, List, Optional

import dearpygui.dearpygui as dpg

from sampletones_application.categories.elements.global_ import (
    GlobalDialogTitleElements,
)
from sampletones_application.categories.elements.settings import AudioSettingsElements
from sampletones_application.categories.hierarchy import Page, Panel, TextType
from sampletones_application.categories.manager import LanguageManager
from sampletones_application.constants.general import TAG_GLOBAL_THEME_DIALOG
from sampletones_application.constants.settings import (
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
from sampletones_application.view_model.shared.audio_settings import (
    BUFFER_SIZE_ITEMS,
    AudioDeviceItem,
    AudioSettingsViewModel,
)
from sampletones_core.constants.audio import BufferSize, SampleRate
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

        self._devices_by_label: Dict[str, AudioDeviceItem] = {}
        self._sample_rates_by_label: Dict[str, SampleRate] = {}
        self._device_items: List[str] = []
        self._current_device_label: str = ""
        self._current_sample_rate_label: str = ""
        self._current_buffer_size_label: str = ""

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
        self._devices_by_label = {device.label: device for device in view_model.devices}
        self._device_items = view_model.device_labels
        self._current_device_label = view_model.current_device_label
        self._current_sample_rate_label = view_model.current_sample_rate_label
        self._current_buffer_size_label = view_model.buffer_size_label

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
                default_value=self._current_device_label,
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
                default_value=self._current_sample_rate_label,
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
                items=list(BUFFER_SIZE_ITEMS),
                default_value=self._current_buffer_size_label,
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
        self._current_device_label = app_data
        self._update_combos()

    def _update_combos(self) -> None:
        if not self._device_items:
            return

        dpg_configure_item(TAG_SETTINGS_AUDIO_COMBO_DEVICE, items=self._device_items)
        device = self._devices_by_label.get(self._current_device_label)
        if device is None:
            dpg_set_value(TAG_SETTINGS_AUDIO_COMBO_DEVICE, "")
            return

        self._sample_rates_by_label = dict(zip(device.sample_rate_labels, device.sample_rates))
        sample_rate_items = list(self._sample_rates_by_label)
        dpg_set_value(TAG_SETTINGS_AUDIO_COMBO_DEVICE, device.label)
        dpg_configure_item(
            TAG_SETTINGS_AUDIO_COMBO_SAMPLE_RATE,
            items=sample_rate_items,
        )

        current_sample_rate_label = dpg.get_value(TAG_SETTINGS_AUDIO_COMBO_SAMPLE_RATE)
        if current_sample_rate_label not in sample_rate_items:
            if device.default_sample_rate_label in sample_rate_items:
                dpg_set_value(
                    TAG_SETTINGS_AUDIO_COMBO_SAMPLE_RATE,
                    device.default_sample_rate_label,
                )
            elif sample_rate_items:
                dpg_set_value(
                    TAG_SETTINGS_AUDIO_COMBO_SAMPLE_RATE,
                    sample_rate_items[0],
                )

    def _refresh_devices(self) -> None:
        self.call(self.on_refresh_devices)

    def _commit(self) -> None:
        device = self._devices_by_label[dpg.get_value(TAG_SETTINGS_AUDIO_COMBO_DEVICE)]
        sample_rate = self._sample_rates_by_label[dpg.get_value(TAG_SETTINGS_AUDIO_COMBO_SAMPLE_RATE)]
        buffer_size = BUFFER_SIZE_ITEMS[dpg.get_value(TAG_SETTINGS_AUDIO_COMBO_BUFFER_SIZE)]
        self.call(self.on_commit, device.device_index, sample_rate, buffer_size)
        self.hide()
