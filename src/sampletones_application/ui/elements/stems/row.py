import dearpygui.dearpygui as dpg

from sampletones_application.categories.context import channel_label
from sampletones_application.categories.manager import LanguageManager
from sampletones_application.layout.general.stems import StemsListLayout
from sampletones_application.layout.glyphs.common import CommonGlyphs
from sampletones_application.tags.general import (
    SUF_BUTTON,
    SUF_CHANNELS,
    SUF_CHECKBOX,
    SUF_GROUP,
    SUF_TEXT,
    SUF_TOOLTIP,
    SUF_TWISTY,
    TAG_GLOBAL_THEME_CHANNEL_MUTED,
    TAG_GLOBAL_THEME_DANGER_BUTTON,
    TAG_GLOBAL_THEME_STEMS_ROW,
    TAG_GLOBAL_THEME_STEMS_ROW_INERT,
)
from sampletones_application.ui.elements.fonts.font import Font
from sampletones_application.ui.elements.fonts.registry import FontRegistry
from sampletones_application.ui.elements.stems.expansion import OpenFolders
from sampletones_application.ui.elements.stems.gestures import StemsGestures
from sampletones_application.ui.elements.stems.messages import StemsMessages
from sampletones_application.ui.elements.stems.offer import StemsListOffer
from sampletones_application.ui.elements.stems.tags import StemsTags
from sampletones_application.ui.themes.channels import (
    CHANNEL_THEME_TAGS,
    PARTIAL_CHANNEL_THEME_TAGS,
)
from sampletones_application.ui.themes.registry import ThemeRegistry
from sampletones_application.utils.gui.dpg import dpg_configure_item, dpg_set_value
from sampletones_application.utils.gui.tooltip import show_tooltip
from sampletones_application.view_model.shared.agreement import Agreement
from sampletones_application.view_model.shared.stems import (
    StemRowViewModel,
    StemsListViewModel,
)
from sampletones_core.constants.enums import ChannelName


class StemRowRenderer:
    """One row of a stems list: the widgets it stands as, and what it currently holds.

    A row is the master box, the name, a box per channel in play, and the button that takes it
    out — whichever of those the list offers. It answers for one row against the view it is drawn
    from, and knows nothing about the bands the rows are grouped into.
    """

    def __init__(
        self,
        tags: StemsTags,
        *,
        layout: StemsListLayout,
        offer: StemsListOffer,
        glyphs: CommonGlyphs,
        open_folders: OpenFolders,
        language_manager: LanguageManager,
        messages: StemsMessages,
        gestures: StemsGestures,
    ) -> None:
        self._tags = tags
        self._layout = layout
        self._offer = offer
        self._glyphs = glyphs
        self._open_folders = open_folders
        self._language_manager = language_manager
        self._messages = messages
        self._gestures = gestures
        self._lbl_remove = language_manager["global.stems.label.remove"]
        self._folder_template = language_manager["global.stems.template.folder_row"]

    def declare_columns(self, view_model: StemsListViewModel) -> None:
        """The columns every band holds to, so the rows line up across the bands."""
        if self._offer.master_box:
            dpg.add_table_column(width_fixed=True, init_width_or_weight=self._layout.master_column_width)

        dpg.add_table_column(width_stretch=True)
        for _channel_name in view_model.channels_in_play:
            dpg.add_table_column(width_fixed=True, init_width_or_weight=self._layout.channel_column_width)

        if self._offer.removal:
            dpg.add_table_column(width_fixed=True, init_width_or_weight=self._layout.remove_button_width)

    def create(self, row: StemRowViewModel, view_model: StemsListViewModel) -> None:
        """Build the widgets one row stands as, in the columns the bands were declared with."""
        with dpg.table_row(tag=self._tags.row(row.key, SUF_GROUP)):
            if self._offer.master_box:
                self._create_master(row)

            self._create_name(row, view_model)
            for channel_name in view_model.channels_in_play:
                self._create_channel(row, channel_name)

            if self._offer.removal:
                self._create_remove(row)

    def repaint(
        self,
        row: StemRowViewModel,
        view_model: StemsListViewModel,
        *,
        releasable: bool,
    ) -> None:
        """Draw what the row currently holds onto the widgets it already stands as.

        A row contributing nothing grays through its theme rather than through ``enabled``, so
        it answers a drag and a right-click as readily as one in play. A box on a channel
        switched off elsewhere takes the muted tone and stays as clickable as any other.
        """
        live = view_model.live
        for channel_name in view_model.boxes_of(row):
            tag = self._tags.channel(row.key, channel_name)
            agreement = row.agreement_on(channel_name)
            dpg_configure_item(tag, enabled=live)
            dpg_set_value(tag, agreement is not Agreement.NONE)
            ThemeRegistry.get(self._channel_theme(channel_name, agreement, view_model)).bind_to_item(tag)

        name_tag = self._tags.row(row.key, SUF_TEXT)
        dpg_set_value(name_tag, row.key == view_model.selected_key)
        dpg_configure_item(name_tag, enabled=live)
        dpg_set_value(self._tags.row(row.key, SUF_TOOLTIP), self._messages.row_explanation(row))
        row_theme = TAG_GLOBAL_THEME_STEMS_ROW if row.in_play else TAG_GLOBAL_THEME_STEMS_ROW_INERT
        ThemeRegistry.get(row_theme).bind_to_item(name_tag)

        if self._offer.master_box:
            master_tag = self._tags.row(row.key, SUF_CHECKBOX)
            dpg_configure_item(master_tag, enabled=live and row.offers_channels)
            dpg_set_value(master_tag, row.takes_part)

        if self._offer.removal:
            dpg_configure_item(self._tags.row(row.key, SUF_BUTTON), enabled=live and releasable)

    def _create_master(self, row: StemRowViewModel) -> None:
        """The box moving every channel the row offers at once."""
        master = dpg.add_checkbox(
            tag=self._tags.row(row.key, SUF_CHECKBOX),
            default_value=row.takes_part,
            user_data=row.key,
            callback=self._gestures.on_master_box,
        )
        self._gestures.bind(master, SUF_CHECKBOX)

    def _create_name(self, row: StemRowViewModel, view_model: StemsListViewModel) -> None:
        """The row itself: what names the source, what you drag it by, and what you drop onto.

        A folder leads with the marker that opens it, and where a list holds one every other row
        opens the same width beside its name, so the names line up down the column.
        """
        with dpg.group(horizontal=True):
            self._create_disclosure(row, view_model)
            name = dpg.add_selectable(
                label=self._row_label(row),
                tag=self._tags.row(row.key, SUF_TEXT),
                user_data=row.key,
                callback=self._gestures.on_name_selected,
                payload_type=self._tags.payload,
                drop_callback=self._gestures.on_row_drop,
            )
            if self._offer.dragging:
                with dpg.drag_payload(parent=name, drag_data=row.key, payload_type=self._tags.payload):
                    dpg.add_text(row.name)

            FontRegistry.bind_to_item(name, Font.BOLD_SMALL if row.stands_for_a_folder else Font.REGULAR_SMALL)
            self._gestures.bind(name, SUF_TEXT)
            show_tooltip(
                name,
                self._messages.row_explanation(row),
                text_tag=self._tags.row(row.key, SUF_TOOLTIP),
            )

    def _create_disclosure(self, row: StemRowViewModel, view_model: StemsListViewModel) -> None:
        """The marker a folder opens by, and the room it takes beside every other row."""
        if not view_model.holds_folders:
            return

        if not row.stands_for_a_folder:
            dpg.add_spacer(width=self._layout.twisty_width)
            return

        twisty = dpg.add_button(
            label=self._twisty_glyph(row.key),
            tag=self._tags.row(row.key, SUF_TWISTY),
            width=self._layout.twisty_width,
            user_data=row.key,
            callback=self._gestures.on_twisty,
        )
        FontRegistry.bind_to_item(twisty, Font.ICON)
        self._gestures.bind(twisty, SUF_TWISTY)

    def _twisty_glyph(self, key: str) -> str:
        """The marker stating whether the folder's recordings are in view."""
        if self._open_folders.stands_open(key):
            return self._glyphs.expanded

        return self._glyphs.collapsed

    def _row_label(self, row: StemRowViewModel) -> str:
        """What the row reads as: the source's name, and for a folder how many it stands for."""
        if not row.stands_for_a_folder:
            return row.name

        return self._folder_template.format(name=row.name, count=row.holds)

    def _create_channel(self, row: StemRowViewModel, channel_name: ChannelName) -> None:
        """The box giving the recording a channel, where the recording holds frames on it.

        A recording holding none on this channel leaves the cell open, so the columns keep
        lining up across the rows while only a reachable choice is drawn.
        """
        if channel_name not in row.offered_channels:
            dpg.add_spacer()
            return

        checkbox_tag = self._tags.channel(row.key, channel_name)
        dpg.add_checkbox(
            label=channel_label(self._language_manager, channel_name),
            tag=checkbox_tag,
            default_value=row.agreement_on(channel_name) is not Agreement.NONE,
            user_data=(row.key, channel_name),
            callback=self._gestures.on_channel_box,
        )
        self._gestures.bind(checkbox_tag, SUF_CHANNELS)

    def _create_remove(self, row: StemRowViewModel) -> None:
        remove = dpg.add_button(
            label=self._lbl_remove,
            tag=self._tags.row(row.key, SUF_BUTTON),
            width=self._layout.remove_button_width,
            user_data=row.key,
            callback=self._gestures.on_remove_button,
        )
        FontRegistry.bind_to_item(remove, Font.MONO_SMALL)
        ThemeRegistry.get(TAG_GLOBAL_THEME_DANGER_BUTTON).bind_to_item(remove)
        self._gestures.bind(remove, SUF_BUTTON)

    def _channel_theme(
        self,
        channel_name: ChannelName,
        agreement: Agreement,
        view_model: StemsListViewModel,
    ) -> str:
        """The tone a channel's box takes: its own color, softened where the row half-holds it,
        muted where a choice made elsewhere has switched the channel off."""
        if channel_name in view_model.muted_channels:
            return TAG_GLOBAL_THEME_CHANNEL_MUTED

        if agreement is Agreement.SOME:
            return PARTIAL_CHANNEL_THEME_TAGS[channel_name]

        return CHANNEL_THEME_TAGS[channel_name]
