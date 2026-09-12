from typing import Any, Callable, Dict, Optional

import dearpygui.dearpygui as dpg

from sampletones_application.categories.manager import LanguageManager
from sampletones_application.constants.conversion import MIN_CHANNEL_CAP
from sampletones_application.constants.output import OutputKind
from sampletones_application.layout.general.inputs import InputsLayout
from sampletones_application.tags.compose import compose_tag
from sampletones_application.tags.general import SUF_HANDLER_REGISTRY
from sampletones_application.tags.main import (
    TAG_MAIN_CONVERTER_COMBO_HIERARCHY_MODE,
    TAG_MAIN_CONVERTER_GROUP_CONTROLS,
    TAG_MAIN_CONVERTER_GROUP_ORDER,
    TAG_MAIN_CONVERTER_INPUT_CHANNEL_CAP,
    TAG_MAIN_CONVERTER_PANEL,
    TAG_MAIN_CONVERTER_RADIO_MODE,
    TAG_MAIN_CONVERTER_TOOLTIP_CHANNEL_CAP,
    TAG_MAIN_CONVERTER_TOOLTIP_HIERARCHY_MODE,
    TAG_MAIN_CONVERTER_TOOLTIP_MODE,
)
from sampletones_application.ui.elements.field import labeled_field
from sampletones_application.ui.elements.fonts.font import Font
from sampletones_application.ui.elements.fonts.registry import FontRegistry
from sampletones_application.utils.gui.dpg import dpg_configure_item, dpg_set_value
from sampletones_application.utils.gui.tooltip import set_tooltip_visible, show_tooltip
from sampletones_application.utils.gui.widgets import clamp_widget_value
from sampletones_application.view_model.main.converter import ConverterViewModel
from sampletones_core.constants.algorithm import DEFAULT_STEMS_HIERARCHY_MODE
from sampletones_core.constants.enums import ChannelName, HierarchyMode
from sampletones_shared.types.application import Sender
from sampletones_shared.utils.callbacks import CallbackMixin


class ConverterSetup(CallbackMixin):
    """What a run is set up as: the output it writes, and the choices that shape it.

    The output switch stands at the head of the card and names the run in words, so the button
    below it and the switch above read as one sentence. The rest — how many channels one recording
    may hold, and the order the levels pick in — answers for a list that already holds something,
    and stands under it.
    """

    def __init__(
        self,
        *,
        inputs: InputsLayout,
        language_manager: LanguageManager,
    ) -> None:
        self._language_manager = language_manager
        self._input_width = inputs.default_width
        self._label_width = inputs.label_width
        self._settings_handler_tag = compose_tag(TAG_MAIN_CONVERTER_PANEL, SUF_HANDLER_REGISTRY)
        self._mode_labels: Dict[OutputKind, str] = {
            OutputKind.PER_RECORDING: language_manager["main.converter.label.mode_each"],
            OutputKind.MIXED: language_manager["main.converter.label.mode_mixed"],
        }
        self._hierarchy_labels: Dict[HierarchyMode, str] = {
            HierarchyMode.ROUND_ROBIN: language_manager["main.converter.label.hierarchy_round_robin"],
            HierarchyMode.STRICT: language_manager["main.converter.label.hierarchy_strict"],
        }

        self.on_output_changed: Optional[Callable[[OutputKind], None]] = None
        self.on_channel_cap_changed: Optional[Callable[[int], None]] = None
        self.on_hierarchy_mode_changed: Optional[Callable[[HierarchyMode], None]] = None

    def create_handlers(self) -> None:
        """Register the handler the channel cap reports its finished edit through."""
        with dpg.item_handler_registry(tag=self._settings_handler_tag):
            dpg.add_item_deactivated_after_edit_handler(callback=self._on_channel_cap_edited)

    def create_output(self) -> None:
        """The switch naming what the run writes, which the card opens on."""
        with labeled_field(self._language_manager["main.converter.label.mode"], self._label_width):
            mode = dpg.add_radio_button(
                items=list(self._mode_labels.values()),
                tag=TAG_MAIN_CONVERTER_RADIO_MODE,
                horizontal=True,
                default_value=self._mode_labels[OutputKind.PER_RECORDING],
                callback=self._on_mode_changed,
            )
            FontRegistry.bind_to_item(mode, Font.REGULAR_SMALL)

        show_tooltip(
            TAG_MAIN_CONVERTER_RADIO_MODE,
            self._language_manager["main.converter.message.mode_tooltip"],
            tag=TAG_MAIN_CONVERTER_TOOLTIP_MODE,
        )

    def create_controls(self) -> None:
        """The choices a list that holds something answers for, which stand below it."""
        with dpg.group(tag=TAG_MAIN_CONVERTER_GROUP_CONTROLS, show=False):
            with labeled_field(self._language_manager["main.converter.label.channel_cap"], self._label_width):
                cap_input = dpg.add_input_int(
                    tag=TAG_MAIN_CONVERTER_INPUT_CHANNEL_CAP,
                    width=self._input_width,
                    min_value=MIN_CHANNEL_CAP,
                    min_clamped=True,
                    max_clamped=True,
                    default_value=len(ChannelName),
                    callback=self._on_channel_cap_edited,
                )
                FontRegistry.bind_to_item(cap_input, Font.MONO)

            with dpg.group(tag=TAG_MAIN_CONVERTER_GROUP_ORDER, show=False):
                with labeled_field(self._language_manager["main.converter.label.hierarchy_mode"], self._label_width):
                    dpg.add_combo(
                        items=list(self._hierarchy_labels.values()),
                        tag=TAG_MAIN_CONVERTER_COMBO_HIERARCHY_MODE,
                        width=self._input_width,
                        default_value=self._hierarchy_labels[DEFAULT_STEMS_HIERARCHY_MODE],
                        callback=self._on_hierarchy_mode_edited,
                    )

        dpg.bind_item_handler_registry(TAG_MAIN_CONVERTER_INPUT_CHANNEL_CAP, self._settings_handler_tag)
        self._attach_tooltips()

    def update_view(self, view_model: ConverterViewModel) -> None:
        """Draw the setup the view names onto the widgets standing for it."""
        dpg_set_value(TAG_MAIN_CONVERTER_RADIO_MODE, self._mode_labels[view_model.output])
        dpg_configure_item(TAG_MAIN_CONVERTER_RADIO_MODE, enabled=not view_model.is_active)
        dpg_configure_item(TAG_MAIN_CONVERTER_GROUP_CONTROLS, show=view_model.listed)
        dpg_configure_item(
            TAG_MAIN_CONVERTER_INPUT_CHANNEL_CAP,
            max_value=view_model.max_channel_cap,
            enabled=not view_model.is_active,
        )
        dpg_set_value(TAG_MAIN_CONVERTER_INPUT_CHANNEL_CAP, view_model.channel_cap)
        dpg_set_value(
            TAG_MAIN_CONVERTER_COMBO_HIERARCHY_MODE,
            self._hierarchy_labels[view_model.hierarchy_mode],
        )
        dpg_configure_item(TAG_MAIN_CONVERTER_GROUP_ORDER, show=view_model.mixes_several)
        set_tooltip_visible(TAG_MAIN_CONVERTER_TOOLTIP_CHANNEL_CAP, view_model.listed)
        set_tooltip_visible(TAG_MAIN_CONVERTER_TOOLTIP_HIERARCHY_MODE, view_model.mixes_several)

    def _attach_tooltips(self) -> None:
        for tag, message, tooltip_tag in (
            (
                TAG_MAIN_CONVERTER_INPUT_CHANNEL_CAP,
                self._language_manager["main.converter.message.channel_cap_tooltip"],
                TAG_MAIN_CONVERTER_TOOLTIP_CHANNEL_CAP,
            ),
            (
                TAG_MAIN_CONVERTER_COMBO_HIERARCHY_MODE,
                self._language_manager["main.converter.message.hierarchy_mode_tooltip"],
                TAG_MAIN_CONVERTER_TOOLTIP_HIERARCHY_MODE,
            ),
        ):
            show_tooltip(tag, message, tag=tooltip_tag)

    def _on_mode_changed(self, _sender: Sender, value: str) -> None:
        """The switch names what the run writes, which the reader states in words."""
        for output, label in self._mode_labels.items():
            if label == value:
                self.call(self.on_output_changed, output)
                return

    def _on_channel_cap_edited(self, _sender: Sender, _app_data: Any) -> None:
        self.call(self.on_channel_cap_changed, int(clamp_widget_value(TAG_MAIN_CONVERTER_INPUT_CHANNEL_CAP)))

    def _on_hierarchy_mode_edited(self, _sender: Sender, value: str) -> None:
        for hierarchy_mode, label in self._hierarchy_labels.items():
            if label == value:
                self.call(self.on_hierarchy_mode_changed, hierarchy_mode)
                return
