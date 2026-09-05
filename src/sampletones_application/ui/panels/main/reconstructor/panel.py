from typing import Any, Callable, Optional

import dearpygui.dearpygui as dpg

from sampletones_application.categories.manager import LanguageManager
from sampletones_application.constants.sources import SettingsField
from sampletones_application.layout.general.inputs import InputsLayout
from sampletones_application.layout.general.stems import StemsListLayout
from sampletones_application.layout.tabs.main.reconstructor import ReconstructorLayout
from sampletones_application.tags.compose import compose_tag
from sampletones_application.tags.general import (
    SUF_HANDLER_REGISTRY,
    TAG_GLOBAL_THEME_SECTION_HEADER,
)
from sampletones_application.tags.main import (
    TAG_MAIN_RECONSTRUCTOR_PANEL,
    TAG_MAIN_RECONSTRUCTOR_SLIDER_DRIVE,
    TAG_MAIN_RECONSTRUCTOR_TEXT_INSPECTING,
    TAG_MAIN_RECONSTRUCTOR_TEXT_UNPICKED,
)
from sampletones_application.ui.elements.field import labeled_field
from sampletones_application.ui.elements.fonts.font import Font
from sampletones_application.ui.elements.fonts.registry import FontRegistry
from sampletones_application.ui.elements.panel import GUIPanel
from sampletones_application.ui.elements.status import GUIStatusBar
from sampletones_application.ui.panels.main.reconstructor.grid import SettingsGrid
from sampletones_application.ui.themes.registry import ThemeRegistry
from sampletones_application.utils.gui.dpg import dpg_configure_item, dpg_set_value
from sampletones_application.utils.gui.tooltip import show_tooltip
from sampletones_application.utils.gui.widgets import clamp_widget_value
from sampletones_application.view_model.main.reconstructor import (
    InspectedSourceViewModel,
    ReconstructorPanelViewModel,
)
from sampletones_application.view_model.main.updates import GenerationSettingsUpdate
from sampletones_core.constants.algorithm import MAX_DRIVE
from sampletones_core.constants.enums import ChannelName
from sampletones_shared.types.application import Sender


class GUIReconstructorPanel(GUIPanel):
    """The settings card: the drive a run holds to, and the choices the picked row is given.

    Drive stands above the rule and answers for the run as a whole, so it is there whatever the
    reader is looking at. Below the rule the card names the row picked out of the converter's
    list and draws its choices as one row of that list's own grid; with nothing picked it says
    which gesture picks one.
    """

    def __init__(
        self,
        initial_view: ReconstructorPanelViewModel,
        *,
        layout: ReconstructorLayout,
        inputs: InputsLayout,
        stems_layout: StemsListLayout,
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
        self._grid = SettingsGrid(layout=stems_layout, language_manager=language_manager)
        self._msg_unpicked = language_manager["main.reconstructor.message.nothing_picked"]
        self._tpl_folder = language_manager["global.stems.template.folder_row"]
        self._item_handler_tag = compose_tag(TAG_MAIN_RECONSTRUCTOR_PANEL, SUF_HANDLER_REGISTRY)

        self.on_generation_settings_changed: Optional[Callable[[GenerationSettingsUpdate], None]] = None
        self.on_slot_toggled: Optional[Callable[[SettingsField, ChannelName], None]] = None
        self.on_channel_keyed: Optional[Callable[[ChannelName], None]] = None

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
            self._create_drive_slider()
            dpg.add_separator()
            self._create_subject_line()
            self._create_unpicked_hint()
            self._grid.create(self._view)
            self._create_tooltips()

        self._grid.on_slot_toggled = self._on_slot_toggled
        self.update_view(self._view)

    def update_view(self, view_model: ReconstructorPanelViewModel) -> None:
        """Take up what the card now edits: the drive, the row picked out, and its choices."""
        self._view = view_model
        dpg.set_value(TAG_MAIN_RECONSTRUCTOR_SLIDER_DRIVE, view_model.drive)
        dpg_set_value(TAG_MAIN_RECONSTRUCTOR_TEXT_INSPECTING, self._subject_text(view_model.inspected))
        dpg_configure_item(TAG_MAIN_RECONSTRUCTOR_TEXT_INSPECTING, show=view_model.inspecting)
        dpg_configure_item(TAG_MAIN_RECONSTRUCTOR_TEXT_UNPICKED, show=not view_model.inspecting)
        dpg_configure_item(self._grid.tag, show=view_model.inspecting)
        self._grid.render(view_model)

    def toggle_channel(self, channel: ChannelName) -> None:
        """Switches one channel across the whole list, which is what its key reaches.

        A box on the card answers for the row a reader picked out; the key answers for the list,
        so setting a channel on everything at once is one press rather than a row at a time.
        """
        self.call(self.on_channel_keyed, channel)

    def _setup_handlers(self) -> None:
        with dpg.item_handler_registry(tag=self._item_handler_tag):
            dpg.add_item_deactivated_handler(callback=self._on_parameter_change)
            dpg.add_item_deactivated_after_edit_handler(callback=self._on_parameter_change)
            dpg.add_item_edited_handler(callback=self._on_parameter_change)

    def _create_subject_line(self) -> None:
        """The row the card is editing, named the way the list names it."""
        text = dpg.add_text(
            self._subject_text(self._view.inspected),
            tag=TAG_MAIN_RECONSTRUCTOR_TEXT_INSPECTING,
        )
        FontRegistry.bind_to_item(text, Font.BOLD)
        ThemeRegistry.get(TAG_GLOBAL_THEME_SECTION_HEADER).bind_to_item(text)

    def _create_unpicked_hint(self) -> None:
        """What to do to give the card something to edit, standing where the row's name stands."""
        text = dpg.add_text(self._msg_unpicked, tag=TAG_MAIN_RECONSTRUCTOR_TEXT_UNPICKED, wrap=self.width)
        FontRegistry.bind_to_item(text, Font.REGULAR_SMALL)

    def _subject_text(self, inspected: Optional[InspectedSourceViewModel]) -> str:
        if inspected is None:
            return ""

        if inspected.stands_for_a_folder:
            return self._tpl_folder.format(name=inspected.name, count=inspected.holds)

        return inspected.name

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

    def _on_slot_toggled(self, field: SettingsField, channel_name: ChannelName) -> None:
        self.call(self.on_slot_toggled, field, channel_name)

    def _on_parameter_change(self, _sender: Sender, _app_data: Any) -> None:
        self._report_generation_settings()

    def _report_generation_settings(self) -> None:
        generation_update = GenerationSettingsUpdate(
            drive=float(clamp_widget_value(TAG_MAIN_RECONSTRUCTOR_SLIDER_DRIVE)),
        )
        self.call(self.on_generation_settings_changed, generation_update)
