from typing import Callable, Dict, Final, FrozenSet, Optional, Tuple

import dearpygui.dearpygui as dpg

from sampletones_application.categories.manager import LanguageManager
from sampletones_application.constants.sources import SettingsField
from sampletones_application.layout.general.stems import StemsListLayout
from sampletones_application.tags.compose import compose_tag
from sampletones_application.tags.main import (
    PRE_MAIN_SOURCE_SLOT,
    TAG_MAIN_SOURCE_GROUP_GRID,
    TAG_MAIN_SOURCE_TABLE_GRID,
)
from sampletones_application.ui.elements.stems.columns import StemsColumns
from sampletones_application.ui.elements.stems.heading import StemsHeading
from sampletones_application.ui.themes.channels import (
    CHANNEL_THEME_TAGS,
    PARTIAL_CHANNEL_THEME_TAGS,
)
from sampletones_application.ui.themes.registry import ThemeRegistry
from sampletones_application.utils.gui.dpg import dpg_configure_item, dpg_set_value
from sampletones_application.view_model.main.source import (
    SettingsSlotViewModel,
    SourceSettingsPanelViewModel,
)
from sampletones_application.view_model.shared.agreement import Agreement
from sampletones_core.constants.enums import ChannelName
from sampletones_shared.types.application import Sender
from sampletones_shared.utils.callbacks import CallbackMixin

SlotCallback = Callable[[SettingsField, ChannelName], None]

NO_MUTED_CHANNELS: Final[FrozenSet[ChannelName]] = frozenset()
SETTINGS_FIELDS: Final[Tuple[SettingsField, ...]] = tuple(SettingsField)


class SettingsGrid(CallbackMixin):
    """The choices a settings card edits, as one row of the grid the converter's list stands in.

    The channels are named once above the row and each cell holds the boxes its channel offers —
    the channel a recording takes, and the bend on it — so the card reads the way a row of the
    list reads and the two share one vocabulary. The row is generated from the slots the model
    declares, which is what makes a further choice one more box in each cell.
    """

    def __init__(
        self,
        *,
        layout: StemsListLayout,
        language_manager: LanguageManager,
    ) -> None:
        self._layout = layout
        self._heading = StemsHeading(
            prefix=TAG_MAIN_SOURCE_GROUP_GRID,
            layout=layout,
            language_manager=language_manager,
            bends=True,
        )
        self._columns = StemsColumns(
            layout=layout,
            channels=tuple(ChannelName.items()),
            master=False,
            removable=False,
            bends=True,
            folders=False,
        )

        self.on_slot_toggled: Optional[SlotCallback] = None

    @property
    def tag(self) -> str:
        """The grid as a whole, which the card shows once a reader has picked a row out."""
        return TAG_MAIN_SOURCE_GROUP_GRID

    def create(self, view_model: SourceSettingsPanelViewModel) -> None:
        """Build the channel names and the one row of boxes standing under them.

        The grid rules its own top edge, which is the line dividing the names from the boxes.
        """
        with dpg.group(tag=TAG_MAIN_SOURCE_GROUP_GRID):
            self._heading.create(TAG_MAIN_SOURCE_GROUP_GRID, self._columns)
            self._heading.render(NO_MUTED_CHANNELS)
            with dpg.table(
                tag=TAG_MAIN_SOURCE_TABLE_GRID,
                header_row=False,
                policy=dpg.mvTable_SizingFixedFit,
                resizable=False,
                borders_innerV=True,
                borders_outerH=True,
            ):
                self._columns.declare()
                self._create_row(view_model)

    def render(self, view_model: SourceSettingsPanelViewModel) -> None:
        """Draw what the picked row currently holds onto the boxes it already stands as."""
        boxes = self._boxes(view_model)
        for field, channel_name in self._cells():
            slot = boxes.get(field)
            self._render_box(field, channel_name, slot, live=view_model.live)

    def _create_row(self, view_model: SourceSettingsPanelViewModel) -> None:
        """One row of the grid: the name column left open, and a cell for every channel."""
        with dpg.table_row():
            self._columns.open_leading_cells()
            boxes = self._boxes(view_model)
            for channel_name in self._columns.channels:
                self._create_cell(channel_name, boxes)

    def _create_cell(
        self,
        channel_name: ChannelName,
        boxes: Dict[SettingsField, SettingsSlotViewModel],
    ) -> None:
        """One channel's boxes, standing in the slots the heading above them names."""
        with dpg.group(horizontal=True, indent=self._columns.box_indent(channel_name)):
            for field in self._fields_on(channel_name):
                self._create_box(field, channel_name, boxes.get(field))

    def _create_box(
        self,
        field: SettingsField,
        channel_name: ChannelName,
        slot: Optional[SettingsSlotViewModel],
    ) -> None:
        checkbox_tag = self._box_tag(field, channel_name)
        dpg.add_checkbox(
            tag=checkbox_tag,
            user_data=(field, channel_name),
            callback=self._on_box,
        )
        self._render_box(field, channel_name, slot, live=True)

    def _render_box(
        self,
        field: SettingsField,
        channel_name: ChannelName,
        slot: Optional[SettingsSlotViewModel],
        *,
        live: bool,
    ) -> None:
        """Draw one box: what its channel reads, in the tone that reading takes."""
        checkbox_tag = self._box_tag(field, channel_name)
        agreement = slot.agreement_on(channel_name) if slot is not None else Agreement.NONE
        offered = slot is not None and slot.offers(channel_name)
        dpg_configure_item(checkbox_tag, show=offered, enabled=live)
        dpg_set_value(checkbox_tag, agreement.reads_held)
        ThemeRegistry.get(self._box_theme(channel_name, agreement)).bind_to_item(checkbox_tag)

    def _cells(self) -> Tuple[Tuple[SettingsField, ChannelName], ...]:
        """Every box the grid stands as, which is what a render walks."""
        return tuple(
            (field, channel_name) for channel_name in self._columns.channels for field in self._fields_on(channel_name)
        )

    def _fields_on(self, channel_name: ChannelName) -> Tuple[SettingsField, ...]:
        """The choices one channel's cell holds, in the order the heading names its slots.

        A cell holds as many boxes as the grid gives its channel slots, and the fields stand in
        the order they are declared in, which is the order the slots that read them stand in.
        """
        return SETTINGS_FIELDS[: self._columns.slots(channel_name)]

    @staticmethod
    def _boxes(view_model: SourceSettingsPanelViewModel) -> Dict[SettingsField, SettingsSlotViewModel]:
        """The choices the card is editing, reachable by the field each answers for."""
        return {slot.field: slot for slot in view_model.slots}

    def _on_box(
        self,
        _sender: Sender,
        _value: bool,
        user_data: Tuple[SettingsField, ChannelName],
    ) -> None:
        field, channel_name = user_data
        self.call(self.on_slot_toggled, field, channel_name)

    @staticmethod
    def _box_theme(channel_name: ChannelName, agreement: Agreement) -> str:
        """The tone a box takes: the channel's own color, softened where the group half-holds it."""
        if agreement is Agreement.SOME:
            return PARTIAL_CHANNEL_THEME_TAGS[channel_name]

        return CHANNEL_THEME_TAGS[channel_name]

    @staticmethod
    def _box_tag(field: SettingsField, channel_name: ChannelName) -> str:
        return compose_tag(PRE_MAIN_SOURCE_SLOT, field.value, channel_name.value)
