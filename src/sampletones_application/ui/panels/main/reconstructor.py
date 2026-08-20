from typing import Any, Callable, List, Optional, Tuple

import dearpygui.dearpygui as dpg

from sampletones_application.categories.context import channel_label
from sampletones_application.categories.manager import LanguageManager
from sampletones_application.layout.general.inputs import InputsLayout
from sampletones_application.layout.tabs.main.reconstructor import ReconstructorLayout
from sampletones_application.tags.compose import compose_tag
from sampletones_application.tags.general import SUF_HANDLER_REGISTRY
from sampletones_application.tags.main import (
    PRE_MAIN_RECONSTRUCTOR_CHANNEL,
    TAG_MAIN_RECONSTRUCTOR_PANEL,
    TAG_MAIN_RECONSTRUCTOR_SLIDER_DRIVE,
)
from sampletones_application.ui.elements.field import labeled_field, subheader
from sampletones_application.ui.elements.fonts.font import Font
from sampletones_application.ui.elements.fonts.registry import FontRegistry
from sampletones_application.ui.elements.panel import GUIPanel
from sampletones_application.ui.elements.status import GUIStatusBar
from sampletones_application.ui.themes.channels import CHANNEL_THEME_TAGS
from sampletones_application.ui.themes.registry import ThemeRegistry
from sampletones_application.utils.gui.dpg import dpg_set_value
from sampletones_application.utils.gui.tooltip import show_tooltip
from sampletones_application.utils.gui.widgets import clamp_widget_value
from sampletones_application.view_model.main.reconstructor import (
    ReconstructorPanelViewModel,
)
from sampletones_application.view_model.main.updates import GenerationSettingsUpdate
from sampletones_core.constants.algorithm import MAX_DRIVE
from sampletones_core.constants.enums import ChannelName
from sampletones_shared.types.application import Sender


class GUIReconstructorPanel(GUIPanel):
    def __init__(
        self,
        initial_view: ReconstructorPanelViewModel,
        *,
        layout: ReconstructorLayout,
        inputs: InputsLayout,
        language_manager: LanguageManager,
        status_bar: GUIStatusBar,
        initial_collapsed: bool = False,
    ) -> None:
        self._language_manager = language_manager
        self._view = initial_view
        self._layout = layout
        self._input_width = inputs.default_width
        self._label_width = inputs.label_width
        self._status_bar = status_bar
        self.on_generation_settings_changed: Optional[Callable[[GenerationSettingsUpdate], None]] = None
        self._item_handler_tag = compose_tag(TAG_MAIN_RECONSTRUCTOR_PANEL, SUF_HANDLER_REGISTRY)

        super().__init__(
            tag=TAG_MAIN_RECONSTRUCTOR_PANEL,
            height=layout.height,
        )
        self._enable_vertical_collapse(initial_collapsed=initial_collapsed)

    def create_panel(self, parent: str) -> None:
        self._setup_handlers()
        with self._collapsible_card(
            parent,
            self._language_manager["main.reconstructor.label.section_settings"],
            glyph=self._glyphs.headers.reconstruction,
            width=self.width,
        ):
            self._create_generator_selection()
            dpg.add_separator()
            self._create_drive_slider()
            self._create_tooltips()

    def _setup_handlers(self) -> None:
        with dpg.item_handler_registry(tag=self._item_handler_tag):
            dpg.add_item_deactivated_handler(callback=self._on_parameter_change)
            dpg.add_item_deactivated_after_edit_handler(callback=self._on_parameter_change)
            dpg.add_item_edited_handler(callback=self._on_parameter_change)

    def _create_generator_selection(self) -> None:
        subheader(self._language_manager["main.reconstructor.label.section_channels"])

        with dpg.group():
            for channel, label, theme_tag in self._channel_chips():
                checkbox_tag = self._get_generator_checkbox_tag(channel)
                dpg.add_checkbox(
                    label=label,
                    default_value=channel in self._view.channels,
                    tag=checkbox_tag,
                    callback=self._on_parameter_change,
                )
                ThemeRegistry.get(theme_tag).bind_to_item(checkbox_tag)

    def _channel_chips(self) -> List[Tuple[ChannelName, str, str]]:
        return [
            (
                channel_name,
                channel_label(self._language_manager, channel_name),
                CHANNEL_THEME_TAGS[channel_name],
            )
            for channel_name in ChannelName.items()
        ]

    def _create_drive_slider(self) -> None:
        with labeled_field(self._language_manager["main.reconstructor.label.slider_drive"], self._label_width):
            dpg.add_slider_float(
                tag=TAG_MAIN_RECONSTRUCTOR_SLIDER_DRIVE,
                min_value=0.0,
                max_value=MAX_DRIVE,
                default_value=self._view.drive,
                width=self._input_width,
                format=self._layout.drive_format,
            )

        dpg.bind_item_handler_registry(
            TAG_MAIN_RECONSTRUCTOR_SLIDER_DRIVE,
            self._item_handler_tag,
        )
        self._status_bar.bind_to_item(
            TAG_MAIN_RECONSTRUCTOR_SLIDER_DRIVE,
            self._language_manager["global.status.message.input"],
        )
        FontRegistry.bind_to_item(
            TAG_MAIN_RECONSTRUCTOR_SLIDER_DRIVE,
            Font.MONO,
        )

    def _create_tooltips(self) -> None:
        show_tooltip(
            TAG_MAIN_RECONSTRUCTOR_SLIDER_DRIVE,
            self._language_manager["main.reconstructor.tooltip.tooltip_drive"],
        )

    def toggle_channel(self, channel: ChannelName) -> None:
        """Switches one channel in or out of the set a reconstruction is built from.

        This is the gesture a click on the channel's checkbox makes, reached by the key the
        channel answers to, so the panel reports the settings either way.
        """
        checkbox_tag = self._get_generator_checkbox_tag(channel)
        dpg_set_value(checkbox_tag, not dpg.get_value(checkbox_tag))
        self._report_generation_settings()

    def _on_parameter_change(self, _sender: Sender, _app_data: Any) -> None:
        self._report_generation_settings()

    def _report_generation_settings(self) -> None:
        channels = [channel for channel in ChannelName if dpg.get_value(self._get_generator_checkbox_tag(channel))]
        generation_update = GenerationSettingsUpdate(
            drive=float(clamp_widget_value(TAG_MAIN_RECONSTRUCTOR_SLIDER_DRIVE)),
            channels=channels,
        )
        self.call(self.on_generation_settings_changed, generation_update)

    def update_view(self, view_model: ReconstructorPanelViewModel) -> None:
        self._view = view_model
        dpg.set_value(TAG_MAIN_RECONSTRUCTOR_SLIDER_DRIVE, view_model.drive)
        for channel in ChannelName:
            dpg_set_value(self._get_generator_checkbox_tag(channel), channel in view_model.channels)

    @staticmethod
    def _get_generator_checkbox_tag(channel: ChannelName) -> str:
        return compose_tag(PRE_MAIN_RECONSTRUCTOR_CHANNEL, channel.value)
