from typing import Any, Callable, Dict, List, Optional

import dearpygui.dearpygui as dpg

from sampletones_application.categories.elements.settings import AudioSettingsElements
from sampletones_application.categories.hierarchy import Page, Panel, TextType
from sampletones_application.categories.manager import LanguageManager
from sampletones_application.layout.settings import SettingsLayout
from sampletones_application.tags.general import TAG_GLOBAL_THEME_DIALOG
from sampletones_application.tags.settings import (
    TAG_SETTINGS_AUDIO_BUTTON_APPLY,
    TAG_SETTINGS_AUDIO_BUTTON_REFRESH,
    TAG_SETTINGS_AUDIO_COMBO_BUFFER_SIZE,
    TAG_SETTINGS_AUDIO_COMBO_DEVICE,
    TAG_SETTINGS_AUDIO_COMBO_SAMPLE_RATE,
    TAG_SETTINGS_AUDIO_SLIDER_MASTER_GAIN,
    TAG_SETTINGS_AUDIO_TEXT_MASTER_GAIN_DB,
    TAG_SETTINGS_AUDIO_WINDOW,
)
from sampletones_application.ui.elements.button import GUIButton
from sampletones_application.ui.elements.field import labeled_field
from sampletones_application.ui.elements.fonts.font import Font
from sampletones_application.ui.elements.fonts.registry import FontRegistry
from sampletones_application.ui.elements.window import GUIWindow
from sampletones_application.ui.themes.registry import ThemeRegistry
from sampletones_application.utils.gui.align import table_wrapper
from sampletones_application.utils.gui.dialog_navigation import (
    DialogKeyboardNavigator,
    FocusStop,
)
from sampletones_application.utils.gui.dpg import dpg_configure_item, dpg_set_value
from sampletones_application.utils.gui.keyboard import KeyRouter
from sampletones_application.view_model.shared.audio_settings import (
    BUFFER_SIZE_ITEMS,
    AudioDeviceItem,
    AudioSettingsViewModel,
    MasterGainReadout,
)
from sampletones_core.constants.audio import BufferSize, SampleRate
from sampletones_shared.constants.audio import (
    DEFAULT_MASTER_GAIN,
    MAX_MASTER_GAIN,
    MIN_MASTER_GAIN,
)
from sampletones_shared.types.application import ColorRGBA, Sender
from sampletones_shared.types.callback import VoidCallback
from sampletones_shared.utils.color import blend


class GUIAudioSettingsWindow(GUIWindow):
    def __init__(
        self,
        *,
        layout: SettingsLayout,
        language_manager: LanguageManager,
        key_router: KeyRouter,
    ) -> None:
        self._layout = layout
        self._router = key_router
        self._dialog_theme = ThemeRegistry.get(TAG_GLOBAL_THEME_DIALOG)
        self._navigator: Optional[DialogKeyboardNavigator] = None

        self.on_commit: Optional[Callable[[int, SampleRate, BufferSize], None]] = None
        self.on_refresh_devices: Optional[VoidCallback] = None
        self.on_master_gain_changed: Optional[Callable[[float], None]] = None

        self._devices_by_label: Dict[str, AudioDeviceItem] = {}
        self._sample_rates_by_label: Dict[str, SampleRate] = {}
        self._device_items: List[str] = []
        self._current_device_label: str = ""
        self._current_sample_rate_label: str = ""
        self._current_buffer_size_label: str = ""
        self._master_gain: float = DEFAULT_MASTER_GAIN

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
        self._fmt_device_label = language_manager[
            Page.SETTINGS,
            Panel.AUDIO,
            TextType.TEMPLATE,
            AudioSettingsElements.DEVICE_LABEL,
        ]
        self._lbl_sample_rate = language_manager[
            Page.SETTINGS,
            Panel.AUDIO,
            TextType.LABEL,
            AudioSettingsElements.SAMPLE_RATE,
        ]
        self._fmt_sample_rate = language_manager[
            Page.SETTINGS,
            Panel.AUDIO,
            TextType.TEMPLATE,
            AudioSettingsElements.SAMPLE_RATE_LABEL,
        ]
        self._lbl_buffer_size = language_manager[
            Page.SETTINGS,
            Panel.AUDIO,
            TextType.LABEL,
            AudioSettingsElements.BUFFER_SIZE,
        ]
        self._lbl_master_gain = language_manager[
            Page.SETTINGS,
            Panel.AUDIO,
            TextType.LABEL,
            AudioSettingsElements.MASTER_GAIN,
        ]
        self._fmt_master_gain_db = language_manager[
            Page.SETTINGS,
            Panel.AUDIO,
            TextType.TEMPLATE,
            AudioSettingsElements.MASTER_GAIN_DB,
        ]
        self._lbl_master_gain_silent = language_manager[
            Page.SETTINGS,
            Panel.AUDIO,
            TextType.MESSAGE,
            AudioSettingsElements.MASTER_GAIN_SILENT,
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
        """Re-seeds the values and repaints the combos and master-gain readout of the open window."""
        self._seed(view_model)
        self._update_combos()
        dpg_set_value(TAG_SETTINGS_AUDIO_SLIDER_MASTER_GAIN, self._master_gain)
        self._render_master_gain_readout(self._master_gain)

    def _seed(self, view_model: AudioSettingsViewModel) -> None:
        self._devices_by_label = {device.label(self._fmt_device_label): device for device in view_model.devices}
        self._device_items = view_model.device_labels(self._fmt_device_label)
        self._current_device_label = view_model.current_device_label(self._fmt_device_label)
        self._current_sample_rate_label = view_model.current_sample_rate_label(self._fmt_sample_rate)
        self._current_buffer_size_label = view_model.buffer_size_label
        self._master_gain = view_model.master_gain

    def create_window(self) -> None:
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
            self._create_master_gain_slider()
            dpg.add_separator()
            self._create_action_buttons()

        for combo_tag in (
            TAG_SETTINGS_AUDIO_COMBO_DEVICE,
            TAG_SETTINGS_AUDIO_COMBO_SAMPLE_RATE,
            TAG_SETTINGS_AUDIO_COMBO_BUFFER_SIZE,
        ):
            self._dialog_theme.bind_to_item(combo_tag)

        self._update_combos()
        self._install_navigation()

    def _install_navigation(self) -> None:
        """Wires Tab/Enter/Escape keyboard navigation over the combos and buttons."""
        self._navigator = DialogKeyboardNavigator(
            window_tag=self.tag,
            stops=[
                FocusStop.field(TAG_SETTINGS_AUDIO_COMBO_DEVICE),
                FocusStop.field(TAG_SETTINGS_AUDIO_COMBO_SAMPLE_RATE),
                FocusStop.field(TAG_SETTINGS_AUDIO_COMBO_BUFFER_SIZE),
                FocusStop.field(TAG_SETTINGS_AUDIO_SLIDER_MASTER_GAIN),
                FocusStop.button(TAG_SETTINGS_AUDIO_BUTTON_REFRESH, self._refresh_devices),
                FocusStop.button(TAG_SETTINGS_AUDIO_BUTTON_APPLY, self._commit),
            ],
            on_escape=self.hide,
            key_router=self._router,
        )
        self._navigator.install()

    def _teardown(self) -> None:
        if self._navigator is not None:
            self._navigator.dispose()
            self._navigator = None

    def _create_device_selection(self) -> None:
        with labeled_field(self._lbl_output_device, self._layout.label_width):
            dpg.add_combo(
                tag=TAG_SETTINGS_AUDIO_COMBO_DEVICE,
                items=self._device_items,
                default_value=self._current_device_label,
                width=self._layout.combo_width,
                callback=self._on_device_changed,
            )

    def _create_sample_rate_selection(self) -> None:
        with labeled_field(self._lbl_sample_rate, self._layout.label_width):
            dpg.add_combo(
                tag=TAG_SETTINGS_AUDIO_COMBO_SAMPLE_RATE,
                items=[],
                default_value=self._current_sample_rate_label,
                width=self._layout.combo_width,
            )

    def _create_buffer_size_selection(self) -> None:
        with labeled_field(self._lbl_buffer_size, self._layout.label_width):
            dpg.add_combo(
                tag=TAG_SETTINGS_AUDIO_COMBO_BUFFER_SIZE,
                items=list(BUFFER_SIZE_ITEMS),
                default_value=self._current_buffer_size_label,
                width=self._layout.combo_width,
            )

    def _create_master_gain_slider(self) -> None:
        """Lays out the live master-gain slider beside a decibel readout that reddens toward clipping.

        The slider carries the linear gain; the readout projects it to decibels and tints from neutral
        toward red as the gain drives past unity, warning that a boost is clipping into the output range.
        """
        readout = self._master_gain_readout(self._master_gain)
        with labeled_field(self._lbl_master_gain, self._layout.label_width):
            dpg.add_slider_float(
                tag=TAG_SETTINGS_AUDIO_SLIDER_MASTER_GAIN,
                min_value=MIN_MASTER_GAIN,
                max_value=MAX_MASTER_GAIN,
                default_value=self._master_gain,
                width=self._layout.combo_width,
                format="%.2f",
                callback=self._on_master_gain_changed,
            )
            dpg.add_text(
                readout.db_label,
                tag=TAG_SETTINGS_AUDIO_TEXT_MASTER_GAIN_DB,
                color=self._clip_warning_color(readout.clip_fraction),
            )

        FontRegistry.bind_to_item(TAG_SETTINGS_AUDIO_SLIDER_MASTER_GAIN, Font.MONO)

    def _on_master_gain_changed(self, _sender: Sender, app_data: float) -> None:
        """Applies the slider's gain live and repaints the decibel readout.

        The gain is pushed straight to the callback so the change is heard on the next row the
        player writes rather than after the render-ahead buffer drains.
        """
        gain = float(app_data)
        self._master_gain = gain
        self._render_master_gain_readout(gain)
        self.call(self.on_master_gain_changed, gain)

    def _render_master_gain_readout(self, gain: float) -> None:
        readout = self._master_gain_readout(gain)
        dpg_set_value(TAG_SETTINGS_AUDIO_TEXT_MASTER_GAIN_DB, readout.db_label)
        dpg_configure_item(
            TAG_SETTINGS_AUDIO_TEXT_MASTER_GAIN_DB,
            color=self._clip_warning_color(readout.clip_fraction),
        )

    def _master_gain_readout(self, gain: float) -> MasterGainReadout:
        return MasterGainReadout.for_gain(
            gain,
            decibel_format=self._fmt_master_gain_db,
            silent_label=self._lbl_master_gain_silent,
        )

    def _clip_warning_color(self, clip_fraction: float) -> ColorRGBA:
        """Reddens the readout colour along the layout gradient by the projected boost fraction."""
        colors = self._layout.master_gain
        return blend(colors.label_color, colors.clip_color, clip_fraction)

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

        self._sample_rates_by_label = dict(zip(device.sample_rate_labels(self._fmt_sample_rate), device.sample_rates))
        sample_rate_items = list(self._sample_rates_by_label)
        dpg_set_value(TAG_SETTINGS_AUDIO_COMBO_DEVICE, device.label(self._fmt_device_label))
        dpg_configure_item(
            TAG_SETTINGS_AUDIO_COMBO_SAMPLE_RATE,
            items=sample_rate_items,
        )

        current_sample_rate_label = dpg.get_value(TAG_SETTINGS_AUDIO_COMBO_SAMPLE_RATE)
        default_sample_rate_label = device.default_sample_rate_label(self._fmt_sample_rate)
        if current_sample_rate_label not in sample_rate_items:
            if default_sample_rate_label in sample_rate_items:
                dpg_set_value(
                    TAG_SETTINGS_AUDIO_COMBO_SAMPLE_RATE,
                    default_sample_rate_label,
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
