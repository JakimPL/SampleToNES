from typing import Any, Callable, Dict, Optional, Tuple

import dearpygui.dearpygui as dpg

from sampletones_application.categories.context import channel_label
from sampletones_application.categories.manager import LanguageManager
from sampletones_application.constants.sources import SettingsField
from sampletones_application.layout.general.inputs import InputsLayout
from sampletones_application.layout.tabs.main.reconstructor import ReconstructorLayout
from sampletones_application.tags.compose import compose_tag
from sampletones_application.tags.general import SUF_HANDLER_REGISTRY
from sampletones_application.tags.main import (
    PRE_MAIN_RECONSTRUCTOR_SLOT,
    TAG_MAIN_RECONSTRUCTOR_PANEL,
    TAG_MAIN_RECONSTRUCTOR_SLIDER_DRIVE,
    TAG_MAIN_RECONSTRUCTOR_TEXT_INSPECTING,
)
from sampletones_application.ui.elements.field import labeled_field, subheader
from sampletones_application.ui.elements.fonts.font import Font
from sampletones_application.ui.elements.fonts.registry import FontRegistry
from sampletones_application.ui.elements.panel import GUIPanel
from sampletones_application.ui.elements.status import GUIStatusBar
from sampletones_application.ui.themes.channels import (
    CHANNEL_THEME_TAGS,
    PARTIAL_CHANNEL_THEME_TAGS,
)
from sampletones_application.ui.themes.registry import ThemeRegistry
from sampletones_application.utils.gui.dpg import dpg_configure_item, dpg_set_value
from sampletones_application.utils.gui.tooltip import show_tooltip
from sampletones_application.utils.gui.widgets import clamp_widget_value
from sampletones_application.view_model.main.reconstructor import (
    ReconstructorPanelViewModel,
    SettingsSlotViewModel,
)
from sampletones_application.view_model.main.updates import GenerationSettingsUpdate
from sampletones_application.view_model.shared.agreement import Agreement
from sampletones_core.constants.algorithm import MAX_DRIVE
from sampletones_core.constants.enums import ChannelName
from sampletones_shared.types.application import Sender


class GUIReconstructorPanel(GUIPanel):
    """The settings card: the per-recording choices a reader edits, and the drive the run holds to.

    The card is drawn from the slots the model declares rather than from a control per field, so a
    further choice reaches the screen as one more slot and one more line naming it. What it edits
    is whatever the list has picked out; with nothing picked it edits the settings a recording
    joins the list with.
    """

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
        self.on_slot_toggled: Optional[Callable[[SettingsField, ChannelName], None]] = None
        self._slot_labels: Dict[SettingsField, str] = {
            SettingsField.CHANNELS: language_manager["main.reconstructor.label.slot_channels"],
            SettingsField.BENDS: language_manager["main.reconstructor.label.slot_bends"],
        }
        self._msg_joining = language_manager["main.reconstructor.message.inspecting_joining"]
        self._tpl_inspecting = language_manager["main.reconstructor.template.inspecting_row"]
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
            self._create_subject_line()
            for slot in self._view.slots:
                self._create_slot(slot)

            dpg.add_separator()
            self._create_drive_slider()
            self._create_tooltips()

    def _setup_handlers(self) -> None:
        with dpg.item_handler_registry(tag=self._item_handler_tag):
            dpg.add_item_deactivated_handler(callback=self._on_parameter_change)
            dpg.add_item_deactivated_after_edit_handler(callback=self._on_parameter_change)
            dpg.add_item_edited_handler(callback=self._on_parameter_change)

    def _create_subject_line(self) -> None:
        """What the card is editing, which the list settles by what a reader picks out of it."""
        text = dpg.add_text(self._subject_text(), tag=TAG_MAIN_RECONSTRUCTOR_TEXT_INSPECTING)
        FontRegistry.bind_to_item(text, Font.REGULAR_SMALL)

    def _create_slot(self, slot: SettingsSlotViewModel) -> None:
        """One choice: its name, and a box on every channel it is put to a reader on."""
        subheader(self._slot_labels[slot.field])
        with dpg.group(tag=self._slot_tag(slot.field)):
            for channel_name in ChannelName.items():
                self._create_slot_box(slot, channel_name)

    def _create_slot_box(self, slot: SettingsSlotViewModel, channel_name: ChannelName) -> None:
        checkbox_tag = self._slot_checkbox_tag(slot.field, channel_name)
        dpg.add_checkbox(
            label=channel_label(self._language_manager, channel_name),
            default_value=slot.agreement_on(channel_name) is not Agreement.NONE,
            tag=checkbox_tag,
            show=slot.offers(channel_name),
            user_data=(slot.field, channel_name),
            callback=self._on_slot_box,
        )
        ThemeRegistry.get(CHANNEL_THEME_TAGS[channel_name]).bind_to_item(checkbox_tag)

    def _subject_text(self) -> str:
        inspected = self._view.inspected
        if inspected is None:
            return self._msg_joining

        return self._tpl_inspecting.format(name=inspected)

    def _on_slot_box(
        self,
        _sender: Sender,
        _value: bool,
        user_data: Tuple[SettingsField, ChannelName],
    ) -> None:
        field, channel_name = user_data
        self.call(self.on_slot_toggled, field, channel_name)

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
        """Switches one channel in or out of what the card is editing.

        This is the gesture a click on the channel's box makes, reached by the key the channel
        answers to, so the panel reports the same choice either way.
        """
        self.call(self.on_slot_toggled, SettingsField.CHANNELS, channel)

    def _on_parameter_change(self, _sender: Sender, _app_data: Any) -> None:
        self._report_generation_settings()

    def _report_generation_settings(self) -> None:
        generation_update = GenerationSettingsUpdate(
            drive=float(clamp_widget_value(TAG_MAIN_RECONSTRUCTOR_SLIDER_DRIVE)),
        )
        self.call(self.on_generation_settings_changed, generation_update)

    def update_view(self, view_model: ReconstructorPanelViewModel) -> None:
        self._view = view_model
        dpg.set_value(TAG_MAIN_RECONSTRUCTOR_SLIDER_DRIVE, view_model.drive)
        dpg_set_value(TAG_MAIN_RECONSTRUCTOR_TEXT_INSPECTING, self._subject_text())
        for slot in view_model.slots:
            self._render_slot(slot)

    def _render_slot(self, slot: SettingsSlotViewModel) -> None:
        """Draw what the choice currently stands at onto the boxes it already has."""
        for channel_name in ChannelName.items():
            checkbox_tag = self._slot_checkbox_tag(slot.field, channel_name)
            agreement = slot.agreement_on(channel_name)
            dpg_configure_item(checkbox_tag, show=slot.offers(channel_name))
            dpg_set_value(checkbox_tag, agreement is not Agreement.NONE)
            ThemeRegistry.get(self._box_theme(channel_name, agreement)).bind_to_item(checkbox_tag)

    @staticmethod
    def _box_theme(channel_name: ChannelName, agreement: Agreement) -> str:
        """The tone a box takes: the channel's own color, softened where the group half-holds it."""
        if agreement is Agreement.SOME:
            return PARTIAL_CHANNEL_THEME_TAGS[channel_name]

        return CHANNEL_THEME_TAGS[channel_name]

    @staticmethod
    def _slot_tag(field: SettingsField) -> str:
        return compose_tag(PRE_MAIN_RECONSTRUCTOR_SLOT, field.value)

    @staticmethod
    def _slot_checkbox_tag(field: SettingsField, channel: ChannelName) -> str:
        return compose_tag(PRE_MAIN_RECONSTRUCTOR_SLOT, field.value, channel.value)
