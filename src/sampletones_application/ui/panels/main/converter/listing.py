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
from sampletones_application.utils.gui.keyboard import (
    PRIORITY_PANEL,
    ActivePredicate,
    KeyEvent,
    KeyRouter,
)
from sampletones_application.utils.gui.shortcuts.ids import ShortcutCategory, ShortcutId
from sampletones_application.utils.gui.shortcuts.source import ShortcutSource
from sampletones_application.view_model.main.converter import ConverterViewModel
from sampletones_core.constants.enums import ChannelName
from sampletones_shared.types.callback import PathCallback, StringCallback, VoidCallback
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

    A row picked out puts the list on the keyboard: while the Main tab is in front and no field
    holds the keys, the list answers the presses its own category names and yields every other, so
    a press it has no action for still reaches the application's shortcuts.
    """

    def __init__(
        self,
        *,
        stems_layout: StemsListLayout,
        glyphs: CommonGlyphs,
        language_manager: LanguageManager,
        status_bar: GUIStatusBar,
        key_router: KeyRouter,
        shortcut_source: ShortcutSource,
        tab_active: ActivePredicate,
    ) -> None:
        self._language_manager = language_manager
        self._router = key_router
        self._shortcuts = shortcut_source
        self._tab_active = tab_active
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
        self.on_selection_cleared: Optional[VoidCallback] = None

        self._router.register(self._on_key_pressed, priority=PRIORITY_PANEL, active=self._keys_active)

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
        self._stems_list.on_selection_cleared = lambda: self.call(self.on_selection_cleared)

    def update_view(self, view_model: ConverterViewModel) -> None:
        """Draw the gathered recordings, with the hint standing while none are.

        A list holding nothing stands its heading and its rules over empty room, so the hint takes
        the whole of that room instead and the list comes back with the first recording gathered.
        """
        dpg_configure_item(TAG_MAIN_CONVERTER_TEXT_STEMS_HINT, show=not view_model.listed)
        dpg_configure_item(self._stems_list.tag, show=view_model.listed)
        self._stems_list.update_view(view_model.stems_list)

    def _on_channels_changed(self, key: str, channels: FrozenSet[ChannelName]) -> None:
        self.call(self.on_source_channels_changed, Path(key), channels)

    def _on_folder_channel_toggled(self, key: str, channel_name: ChannelName) -> None:
        """A folder's box moves every recording it stands for, whichever way they were standing."""
        self.call(self.on_folder_channel_toggled, Path(key), channel_name)

    def _on_selected(self, key: str) -> None:
        """A clicked row is the one the settings card inspects."""
        row = self._stems_list.row(key)
        if row is not None:
            self.call(self.on_row_selected, Path(key), row.kind)

    def _keys_active(self) -> bool:
        """Whether the list owns the next key: its tab is in front and it holds a row picked out.

        A row picked out outlives a move to another tab, so the tab is read at the moment of the
        press. A modal dialog claims keys above this scope in the router, which is what holds the
        list off while one stands open.
        """
        return self._tab_active() and self._stems_list.picked_key is not None and not self._router.is_field_focused

    def _on_key_pressed(self, event: KeyEvent) -> bool:
        """Act on the row picked out, reporting whether the list consumed the press.

        The scheme says which press each of the list's actions answers to; a press its category
        leaves unnamed goes on to the application's shortcuts, as does one naming a move the list
        is standing inert against.
        """
        key = self._stems_list.picked_key
        if key is None:
            return False

        match self._shortcuts.action(ShortcutCategory.SOURCES, event):
            case ShortcutId.SOURCES_REMOVE_SOURCE if self._stems_list.lets_a_row_go:
                self._on_removed(key)
            case _:
                return False

        return True

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
