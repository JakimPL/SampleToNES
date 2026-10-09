from typing import Optional

import dearpygui.dearpygui as dpg

from sampletones_application.categories.manager import LanguageManager
from sampletones_application.constants.sources import SettingsField
from sampletones_application.layout.general.inputs import InputsLayout
from sampletones_application.layout.tabs.main.source import SourceSettingsLayout
from sampletones_application.tags.general import TAG_GLOBAL_THEME_SECTION_HEADER
from sampletones_application.tags.main import (
    TAG_MAIN_SOURCE_PANEL,
    TAG_MAIN_SOURCE_TEXT_SUBJECT,
    TAG_MAIN_SOURCE_TOOLTIP_SUBJECT,
)
from sampletones_application.ui.elements.fonts.font import Font
from sampletones_application.ui.elements.fonts.registry import FontRegistry
from sampletones_application.ui.elements.panel import GUIPanel
from sampletones_application.ui.elements.status import GUIStatusBar
from sampletones_application.ui.panels.main.source.rows import ChannelSettingsRows, DriveCallback, SlotCallback
from sampletones_application.ui.panels.main.source.steps import ChannelCapSteps, StepCallback
from sampletones_application.ui.themes.registry import ThemeRegistry
from sampletones_application.utils.gui.dpg import dpg_set_value
from sampletones_application.utils.gui.tooltip import set_tooltip_visible, show_tooltip
from sampletones_application.view_model.main.source import SourceSettingsPanelViewModel
from sampletones_core.constants.enums import ChannelName


class GUISourceSettingsPanel(GUIPanel):
    """The source settings card: what one recording, one folder, or every new recording converts with.

    The card names what it edits — the row picked out of the converter's list, or the recordings a
    reader adds next — and lays each channel out as a line of its own, with how many of them a
    recording may sound at once below. It settles nothing itself: every gesture names the choice
    and hands it on, and the card draws whatever reading it is given back.
    """

    def __init__(
        self,
        initial_view: SourceSettingsPanelViewModel,
        *,
        layout: SourceSettingsLayout,
        inputs: InputsLayout,
        language_manager: LanguageManager,
        status_bar: GUIStatusBar,
        initial_collapsed: bool = False,
    ) -> None:
        self._language_manager = language_manager
        self._view = initial_view
        self._rows = ChannelSettingsRows(layout=layout, language_manager=language_manager, status_bar=status_bar)
        self._steps = ChannelCapSteps(
            layout=layout,
            inputs=inputs,
            language_manager=language_manager,
            status_bar=status_bar,
        )
        self._lbl_new_recordings = language_manager["main.source.label.new_recordings"]
        self._msg_new_recordings = language_manager["main.source.tooltip.tooltip_new_recordings"]
        self._tpl_folder = language_manager["global.stems.template.folder_row"]

        self.on_slot_toggled: Optional[SlotCallback] = None
        self.on_drive_changed: Optional[DriveCallback] = None
        self.on_channel_cap_changed: Optional[StepCallback] = None

        super().__init__(tag=TAG_MAIN_SOURCE_PANEL)
        self._enable_vertical_collapse(initial_collapsed=initial_collapsed, auto_height=True)
        self._wire()

    def create_panel(self, parent: str) -> None:
        with self._collapsible_card(
            parent,
            self._language_manager["main.source.label.section_settings"],
            glyph=self._glyphs.headers.reconstruction,
            width=self.width,
            no_scrollbar=True,
        ):
            self._create_subject_line()
            self._rows.create(self._view)
            self._steps.create()

        self.update_view(self._view)

    def update_view(self, view_model: SourceSettingsPanelViewModel) -> None:
        """Take up what the card now edits and draw every choice the way the recordings read."""
        self._view = view_model
        dpg_set_value(TAG_MAIN_SOURCE_TEXT_SUBJECT, self._subject_text(view_model))
        set_tooltip_visible(TAG_MAIN_SOURCE_TOOLTIP_SUBJECT, view_model.edits_new_recordings)
        self._rows.render(view_model)
        self._steps.render(view_model)

    def _create_subject_line(self) -> None:
        """What the card edits, named the way the list names a row."""
        text = dpg.add_text(self._subject_text(self._view), tag=TAG_MAIN_SOURCE_TEXT_SUBJECT)
        FontRegistry.bind_to_item(text, Font.BOLD)
        ThemeRegistry.get(TAG_GLOBAL_THEME_SECTION_HEADER).bind_to_item(text)
        show_tooltip(TAG_MAIN_SOURCE_TEXT_SUBJECT, self._msg_new_recordings, tag=TAG_MAIN_SOURCE_TOOLTIP_SUBJECT)

    def _subject_text(self, view_model: SourceSettingsPanelViewModel) -> str:
        subject = view_model.subject
        if subject is None:
            return self._lbl_new_recordings

        if subject.stands_for_a_folder:
            return self._tpl_folder.format(name=subject.name, count=subject.holds)

        return subject.name

    def _wire(self) -> None:
        """Hand each section's reports on to the card's own hooks, which the coordinator wires."""
        self._rows.on_slot_toggled = self._on_slot_toggled
        self._rows.on_drive_changed = self._on_drive_changed
        self._steps.on_channel_cap_changed = self._on_channel_cap_changed

    def _on_slot_toggled(self, field: SettingsField, channel_name: ChannelName) -> None:
        self.call(self.on_slot_toggled, field, channel_name)

    def _on_drive_changed(self, channel_name: ChannelName, drive: float) -> None:
        self.call(self.on_drive_changed, channel_name, drive)

    def _on_channel_cap_changed(self, channel_cap: int) -> None:
        self.call(self.on_channel_cap_changed, channel_cap)
