import dearpygui.dearpygui as dpg

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
    TAG_GLOBAL_THEME_STEMS_GROUP_ROW,
    TAG_GLOBAL_THEME_STEMS_MARKER,
    TAG_GLOBAL_THEME_STEMS_PICK,
    TAG_GLOBAL_THEME_STEMS_PICK_PARTIAL,
    TAG_GLOBAL_THEME_STEMS_ROW,
    TAG_GLOBAL_THEME_STEMS_ROW_INERT,
)
from sampletones_application.ui.elements.fonts.font import Font
from sampletones_application.ui.elements.fonts.registry import FontRegistry
from sampletones_application.ui.elements.stems.columns import NO_INDENT, StemsColumns
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

    def create(
        self,
        row: StemRowViewModel,
        view_model: StemsListViewModel,
        columns: StemsColumns,
    ) -> None:
        """Build the widgets one row stands as, in the columns its grid was declared with.

        A folder's row takes a band of its own behind it, so a group reads apart from the
        recordings standing loose around it without spending a pixel of the list's height.
        """
        with dpg.table_row(tag=self._tags.row(row.key, SUF_GROUP)) as line:
            if row.stands_for_a_folder:
                ThemeRegistry.get(TAG_GLOBAL_THEME_STEMS_GROUP_ROW).bind_to_item(line)

            if self._offer.master_box:
                self._create_master(row, view_model, columns)

            self._create_name(row, view_model, columns)
            for channel_name in view_model.channels_in_play:
                self._create_channel(row, channel_name, columns)

            if self._offer.removal:
                self._create_remove(row)

            if columns.reserve_width > 0:
                dpg.add_spacer()

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

        A folder reads out how many recordings it stands for, so its label is written here as well
        as at the draw: a recording leaving the folder is answered inside the folder's own region,
        and the count on the row above it follows from the same reading.
        """
        live = view_model.live
        for channel_name in view_model.boxes_of(row):
            tag = self._tags.channel(row.key, channel_name)
            agreement = row.agreement_on(channel_name)
            dpg_configure_item(tag, enabled=live)
            dpg_set_value(tag, agreement.reads_held)
            ThemeRegistry.get(self._channel_theme(channel_name, agreement, view_model)).bind_to_item(tag)

        name_tag = self._tags.row(row.key, SUF_TEXT)
        dpg_set_value(name_tag, row.key == view_model.selected_key)
        dpg_configure_item(name_tag, enabled=live, label=self._row_label(row))
        dpg_set_value(self._tags.row(row.key, SUF_TOOLTIP), self._messages.row_explanation(row))
        row_theme = TAG_GLOBAL_THEME_STEMS_ROW if row.in_play else TAG_GLOBAL_THEME_STEMS_ROW_INERT
        ThemeRegistry.get(row_theme).bind_to_item(name_tag)

        if self._offer.master_box:
            master_tag = self._tags.row(row.key, SUF_CHECKBOX)
            dpg_configure_item(master_tag, enabled=live and self._master_reaches(row, view_model))
            dpg_set_value(master_tag, self._master_value(row, view_model))
            self._tone_master(row, view_model)

        if self._offer.removal:
            dpg_configure_item(self._tags.row(row.key, SUF_BUTTON), enabled=live and releasable)

    def _create_master(
        self,
        row: StemRowViewModel,
        view_model: StemsListViewModel,
        columns: StemsColumns,
    ) -> None:
        """The box beside the row: what picks it for a mix, or what moves its channels at once."""
        master = dpg.add_checkbox(
            tag=self._tags.row(row.key, SUF_CHECKBOX),
            indent=columns.master_indent,
            default_value=self._master_value(row, view_model),
            user_data=row.key,
            callback=self._gestures.on_pick_box if self._offer.picking else self._gestures.on_master_box,
        )
        self._gestures.bind(master, SUF_CHECKBOX)
        self._tone_master(row, view_model)

    def _master_reaches(self, row: StemRowViewModel, view_model: StemsListViewModel) -> bool:
        """Whether the box beside the row answers a click: the pick has room, or the row has boxes."""
        if self._offer.picking:
            return view_model.reaches(row)

        return row.offers_channels

    def _master_value(self, row: StemRowViewModel, view_model: StemsListViewModel) -> bool:
        """What the box beside the row reads: whether it is picked, or whether it takes part."""
        if self._offer.picking:
            return view_model.picking_of(row).reads_held

        return row.takes_part

    def _tone_master(self, row: StemRowViewModel, view_model: StemsListViewModel) -> None:
        """Fill a picking box where the folder it stands for is picked only in part.

        A tick states an answer the folder has yet to give, so a half-picked one reads clear and
        takes the accent as a fill instead: the reader sees at a glance that some of what the
        folder holds is going into the mix, and one click settles the whole of it either way.
        """
        if not self._offer.picking:
            return

        agreement = view_model.picking_of(row)
        theme = TAG_GLOBAL_THEME_STEMS_PICK_PARTIAL if agreement is Agreement.SOME else TAG_GLOBAL_THEME_STEMS_PICK
        ThemeRegistry.get(theme).bind_to_item(self._tags.row(row.key, SUF_CHECKBOX))

    def _create_name(
        self,
        row: StemRowViewModel,
        view_model: StemsListViewModel,
        columns: StemsColumns,
    ) -> None:
        """The row itself: what names the source, what you drag it by, and what you drop onto.

        A folder leads with the marker that opens it, and a recording standing loose beside one
        opens where that marker's glyph does, so the names read as one column. The name takes the
        height its boxes take, so the band a row reads as covers the whole of what stands beside it.
        """
        with dpg.group(horizontal=True):
            self._create_disclosure(row)
            name = dpg.add_selectable(
                label=self._row_label(row),
                tag=self._tags.row(row.key, SUF_TEXT),
                height=self._layout.name_height,
                indent=self._name_indent(row, columns),
                user_data=row.key,
                callback=self._gestures.on_name_selected,
                payload_type=self._tags.payload,
                drop_callback=self._gestures.on_row_drop,
            )
            if self._draggable(view_model):
                with dpg.drag_payload(parent=name, drag_data=row.key, payload_type=self._tags.payload):
                    dpg.add_text(row.name)

            FontRegistry.bind_to_item(name, Font.BOLD_SMALL if row.stands_for_a_folder else Font.REGULAR_SMALL)
            self._gestures.bind(name, SUF_TEXT)
            show_tooltip(
                name,
                self._messages.row_explanation(row),
                text_tag=self._tags.row(row.key, SUF_TOOLTIP),
            )

    def _name_indent(self, row: StemRowViewModel, columns: StemsColumns) -> int:
        """How far the row's name sits in: a folder opens at its marker, anything else at the glyph."""
        if row.stands_for_a_folder:
            return NO_INDENT

        return columns.marker_indent(self._glyphs.collapsed, Font.ICON)

    def _draggable(self, view_model: StemsListViewModel) -> bool:
        """A row is dragged where the list bands its rows, which is what a drag rearranges."""
        return self._offer.dragging and not view_model.collapse_levels

    def _create_disclosure(self, row: StemRowViewModel) -> None:
        """The marker a folder opens by, which stands beside the folder's own name.

        The marker is drawn to the height of the name it leads and spends no padding around its
        glyph, which stands a folder's row in the rhythm every other row keeps. Its own frame is
        the room it was given, so what the pointer shades is the marker and nothing beside it.
        """
        if not row.stands_for_a_folder:
            return

        twisty = dpg.add_button(
            label=self._twisty_glyph(row.key),
            tag=self._tags.row(row.key, SUF_TWISTY),
            width=self._layout.twisty_width,
            height=self._layout.name_height,
            user_data=row.key,
            callback=self._gestures.on_twisty,
        )
        FontRegistry.bind_to_item(twisty, Font.ICON)
        ThemeRegistry.get(TAG_GLOBAL_THEME_STEMS_MARKER).bind_to_item(twisty)
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

    def _create_channel(
        self,
        row: StemRowViewModel,
        channel_name: ChannelName,
        columns: StemsColumns,
    ) -> None:
        """The box giving the recording a channel, where the recording holds frames on it.

        The box carries no label of its own: the heading names the channel once for the whole
        column, and the box stands in the middle of that column under it. A recording holding no
        frames on this channel leaves the cell open, so the columns keep lining up across the rows
        while only a reachable choice is drawn.
        """
        if channel_name not in row.offered_channels:
            dpg.add_spacer()
            return

        checkbox_tag = self._tags.channel(row.key, channel_name)
        with dpg.group(horizontal=True, indent=columns.box_indent(channel_name)):
            dpg.add_checkbox(
                tag=checkbox_tag,
                default_value=row.agreement_on(channel_name).reads_held,
                user_data=(row.key, channel_name),
                callback=self._gestures.on_channel_box,
            )
            self._create_bend(row, channel_name, columns)

        self._gestures.bind(checkbox_tag, SUF_CHANNELS)

    def _create_bend(
        self,
        row: StemRowViewModel,
        channel_name: ChannelName,
        columns: StemsColumns,
    ) -> None:
        """The box stating the bend the recording carried on this channel, where the list draws one.

        A list describing a conversion that has already run states what it took, so the box reports
        rather than asks: the choice was made when the reconstruction was written.
        """
        if not columns.bends or channel_name not in row.bendable_channels:
            return

        dpg.add_checkbox(
            tag=self._tags.bend(row.key, channel_name),
            default_value=channel_name in row.bends,
            enabled=False,
        )

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
