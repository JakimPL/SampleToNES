from pathlib import Path
from typing import Callable, FrozenSet, Optional

import dearpygui.dearpygui as dpg

from sampletones_application.categories.manager import LanguageManager
from sampletones_application.constants.sources import SourceKind
from sampletones_application.layout.general.stems import StemsListLayout
from sampletones_application.layout.glyphs.common import CommonGlyphs
from sampletones_application.tags.main import (
    PRE_MAIN_CONVERTER_STEMS,
    TAG_MAIN_CONVERTER_TEXT_STEMS_HINT,
    TAG_MAIN_CONVERTER_WINDOW_STEMS,
)
from sampletones_application.ui.elements.fonts.font import Font
from sampletones_application.ui.elements.fonts.registry import FontRegistry
from sampletones_application.ui.elements.status import GUIStatusBar
from sampletones_application.ui.elements.stems.list import GUIStemsList
from sampletones_application.ui.elements.stems.offer import GATHERED_SOURCES
from sampletones_application.utils.gui.dpg import dpg_configure_item
from sampletones_application.view_model.main.converter import ConverterViewModel
from sampletones_core.constants.enums import ChannelName
from sampletones_shared.types.callback import PathCallback, StringCallback
from sampletones_shared.utils.callbacks import CallbackMixin

ChannelsCallback = Callable[[Path, FrozenSet[ChannelName]], None]
ChannelCallback = Callable[[Path, ChannelName], None]
RowCallback = Callable[[Path, SourceKind], None]
PathPairCallback = Callable[[Path, Path], None]
PathOffsetCallback = Callable[[Path, int], None]


class ConverterListing(CallbackMixin):
    """What a run converts: the gathered recordings, and the hint standing where none are.

    The list reports its gestures by the key a row is drawn under, and this is where that key
    becomes the path the logic answers for — including the two a folder answers differently:
    removing one takes everything it holds, and its box settles every recording under it.
    """

    def __init__(
        self,
        *,
        stems_layout: StemsListLayout,
        glyphs: CommonGlyphs,
        language_manager: LanguageManager,
        status_bar: GUIStatusBar,
    ) -> None:
        self._language_manager = language_manager
        self._stems_list = GUIStemsList(
            prefix=PRE_MAIN_CONVERTER_STEMS,
            layout=stems_layout,
            ceiling=stems_layout.well_ceiling,
            glyphs=glyphs,
            language_manager=language_manager,
            status_bar=status_bar,
            offer=GATHERED_SOURCES,
        )

        self.on_source_channels_changed: Optional[ChannelsCallback] = None
        self.on_folder_channel_toggled: Optional[ChannelCallback] = None
        self.on_row_selected: Optional[RowCallback] = None
        self.on_source_removed: Optional[PathCallback] = None
        self.on_folder_removed: Optional[PathCallback] = None
        self.on_source_played: Optional[PathCallback] = None
        self.on_source_dropped_on_source: Optional[PathPairCallback] = None
        self.on_source_dropped_on_level: Optional[PathOffsetCallback] = None
        self.on_menu_requested: Optional[StringCallback] = None

    @property
    def stems_list(self) -> GUIStemsList:
        """The list the gathered recordings are drawn in, which is what addresses their widgets."""
        return self._stems_list

    def create(self) -> None:
        """Build the hint and the list below it, and take up the gestures the list reports."""
        with dpg.group(tag=TAG_MAIN_CONVERTER_WINDOW_STEMS):
            hint = dpg.add_text(
                self._language_manager["main.converter.message.stems_empty_hint"],
                tag=TAG_MAIN_CONVERTER_TEXT_STEMS_HINT,
                wrap=0,
            )
            FontRegistry.bind_to_item(hint, Font.REGULAR_SMALL)
            self._stems_list.create(TAG_MAIN_CONVERTER_WINDOW_STEMS)

        self._stems_list.on_channels_changed = self._on_channels_changed
        self._stems_list.on_channel_toggled = self._on_folder_channel_toggled
        self._stems_list.on_remove_requested = self._on_removed
        self._stems_list.on_row_activated = self._on_selected
        self._stems_list.on_menu_requested = lambda key: self.call(self.on_menu_requested, key)
        self._stems_list.on_row_opened = lambda key: self.call(self.on_source_played, Path(key))
        self._stems_list.on_dropped_on_row = self._on_dropped_on_row
        self._stems_list.on_dropped_on_level = self._on_dropped_on_level

    def update_view(self, view_model: ConverterViewModel) -> None:
        """Draw the gathered recordings, with the hint standing while none are."""
        dpg_configure_item(TAG_MAIN_CONVERTER_TEXT_STEMS_HINT, show=not view_model.listed)
        self._stems_list.update_view(view_model.stems_list)

    def _on_channels_changed(self, key: str, channels: FrozenSet[ChannelName]) -> None:
        self.call(self.on_source_channels_changed, Path(key), channels)

    def _on_folder_channel_toggled(self, key: str, channel_name: ChannelName) -> None:
        """A folder's box moves every recording it stands for, whichever way they were standing."""
        self.call(self.on_folder_channel_toggled, Path(key), channel_name)

    def _on_selected(self, key: str) -> None:
        """A clicked row is the one the settings card inspects, whichever kind it is."""
        row = self._stems_list.row(key)
        if row is not None:
            self.call(self.on_row_selected, Path(key), row.kind)

    def _on_removed(self, key: str) -> None:
        """Taking a folder out takes everything it holds, which is a move of its own."""
        row = self._stems_list.row(key)
        if row is not None and row.stands_for_a_folder:
            self.call(self.on_folder_removed, Path(key))
            return

        self.call(self.on_source_removed, Path(key))

    def _on_dropped_on_row(self, key: str, target_key: str) -> None:
        self.call(self.on_source_dropped_on_source, Path(key), Path(target_key))

    def _on_dropped_on_level(self, key: str, position: int) -> None:
        self.call(self.on_source_dropped_on_level, Path(key), position)
