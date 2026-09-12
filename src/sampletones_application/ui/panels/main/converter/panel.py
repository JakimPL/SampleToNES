from pathlib import Path
from typing import Callable, FrozenSet, Optional

import dearpygui.dearpygui as dpg

from sampletones_application.categories.manager import LanguageManager
from sampletones_application.constants.output import OutputKind
from sampletones_application.constants.sources import SourceKind
from sampletones_application.layout.general.colors.path import PathColors
from sampletones_application.layout.general.inputs import InputsLayout
from sampletones_application.layout.general.stems import StemsListLayout
from sampletones_application.layout.tabs.main.converter import ConverterLayout
from sampletones_application.tags.general import TAG_GLOBAL_THEME_PANEL_EMPHASIS
from sampletones_application.tags.main import TAG_MAIN_CONVERTER_PANEL
from sampletones_application.ui.elements.panel import GUIPanel
from sampletones_application.ui.elements.path import GUIDestinationPathText, GUIPathText
from sampletones_application.ui.elements.status import GUIStatusBar
from sampletones_application.ui.elements.stems.list import GUIStemsList
from sampletones_application.ui.panels.main.converter.action import ConverterActionButton
from sampletones_application.ui.panels.main.converter.listing import ConverterListing
from sampletones_application.ui.panels.main.converter.menus import ConverterMenus
from sampletones_application.ui.panels.main.converter.setup import ConverterSetup
from sampletones_application.ui.panels.main.converter.summary import ConverterSummary
from sampletones_application.utils.gui.keyboard import ActivePredicate, KeyRouter
from sampletones_application.utils.gui.shortcuts.source import ShortcutSource
from sampletones_application.view_model.main.converter import ConverterViewModel
from sampletones_core.constants.enums import ChannelName, HierarchyMode
from sampletones_shared.types.callback import PathCallback, VoidCallback

PathOffsetCallback = Callable[[Path, int], None]


class GUIConverterPanel(GUIPanel):
    """The card a conversion is set up on: what it writes, what it converts, and how far it is.

    The card reads top to bottom as one sentence. The output switch says what a run writes, the
    button below repeats it in the words of what is listed, and the list itself is what the run
    converts. The choices that shape a run stand under the list, since they answer for what it
    holds, and the destination stands under them.
    """

    def __init__(
        self,
        *,
        layout: ConverterLayout,
        stems_layout: StemsListLayout,
        inputs: InputsLayout,
        path_colors: PathColors,
        initial_collapsed: bool = False,
        language_manager: LanguageManager,
        status_bar: GUIStatusBar,
        key_router: KeyRouter,
        shortcut_source: ShortcutSource,
        tab_active: ActivePredicate,
    ) -> None:
        self._language_manager = language_manager
        self._setup = ConverterSetup(inputs=inputs, language_manager=language_manager)
        self._listing = ConverterListing(
            stems_layout=stems_layout,
            glyphs=self._glyphs.common,
            language_manager=language_manager,
            status_bar=status_bar,
            key_router=key_router,
            shortcut_source=shortcut_source,
            tab_active=tab_active,
        )
        self._menus = ConverterMenus(
            stems_list=self._listing.stems_list,
            language_manager=language_manager,
            shortcut_source=shortcut_source,
        )
        self._action = ConverterActionButton(
            layout=layout,
            language_manager=language_manager,
            status_bar=status_bar,
        )
        self._summary = ConverterSummary(
            path_colors=path_colors,
            language_manager=language_manager,
            status_bar=status_bar,
        )
        self._banded = False

        self.on_convert_requested: Optional[VoidCallback] = None
        self.on_cancel_requested: Optional[VoidCallback] = None
        self.on_output_changed: Optional[Callable[[OutputKind], None]] = None
        self.on_channel_cap_changed: Optional[Callable[[int], None]] = None
        self.on_hierarchy_mode_changed: Optional[Callable[[HierarchyMode], None]] = None
        self.on_source_channels_changed: Optional[Callable[[Path, FrozenSet[ChannelName]], None]] = None
        self.on_folder_channel_toggled: Optional[Callable[[Path, ChannelName], None]] = None
        self.on_row_selected: Optional[Callable[[Path, SourceKind], None]] = None
        self.on_selection_cleared: Optional[VoidCallback] = None
        self.on_source_removed: Optional[PathCallback] = None
        self.on_folder_removed: Optional[PathCallback] = None
        self.on_source_moved: Optional[PathOffsetCallback] = None
        self.on_source_level_joined: Optional[PathOffsetCallback] = None
        self.on_source_isolated: Optional[PathCallback] = None
        self.on_source_dropped_on_source: Optional[Callable[[Path, Path], None]] = None
        self.on_source_dropped_on_level: Optional[PathOffsetCallback] = None
        self.on_source_played: Optional[PathCallback] = None

        super().__init__(tag=TAG_MAIN_CONVERTER_PANEL)
        self._enable_vertical_collapse(initial_collapsed=initial_collapsed, auto_height=True)
        self._wire()

    def create_panel(self, parent: str) -> None:
        self._setup.create_handlers()
        with self._collapsible_card(
            parent,
            self._language_manager["main.converter.label.section"],
            glyph=self._glyphs.headers.converter,
            width=self.width,
            no_scrollbar=True,
            card_theme=TAG_GLOBAL_THEME_PANEL_EMPHASIS,
        ):
            self._setup.create_output()
            self._action.create()
            dpg.add_separator()
            self._listing.create()
            self._setup.create_controls()
            self._summary.create_paths()
            dpg.add_separator()
            self._summary.create_status()

    @property
    def stems_list(self) -> GUIStemsList:
        """The list the gathered recordings are drawn in, which is what addresses their widgets."""
        return self._listing.stems_list

    @property
    def input_path_text(self) -> Optional[GUIPathText]:
        """The line naming the recording a running conversion is on."""
        return self._summary.input_path_text

    @property
    def output_path_text(self) -> Optional[GUIDestinationPathText]:
        """The line naming where a run writes."""
        return self._summary.output_path_text

    def is_visible(self) -> bool:
        return bool(dpg.get_item_configuration(self.tag)["show"])

    def update_view(self, view_model: ConverterViewModel) -> None:
        self._banded = view_model.mixes
        self._action.update_view(view_model)
        self._summary.update_view(view_model)
        self._setup.update_view(view_model)
        self._listing.update_view(view_model)

    def _wire(self) -> None:
        """Hand each section's reports on to the card's own hooks, which the coordinator wires."""
        self._setup.on_output_changed = lambda output: self.call(self.on_output_changed, output)
        self._setup.on_channel_cap_changed = lambda cap: self.call(self.on_channel_cap_changed, cap)
        self._setup.on_hierarchy_mode_changed = lambda mode: self.call(self.on_hierarchy_mode_changed, mode)

        self._action.on_convert_requested = lambda: self.call(self.on_convert_requested)
        self._action.on_cancel_requested = lambda: self.call(self.on_cancel_requested)

        self._listing.on_source_channels_changed = lambda path, channels: self.call(
            self.on_source_channels_changed, path, channels
        )
        self._listing.on_folder_channel_toggled = lambda path, channel: self.call(
            self.on_folder_channel_toggled, path, channel
        )
        self._listing.on_row_selected = lambda path, kind: self.call(self.on_row_selected, path, kind)
        self._listing.on_selection_cleared = lambda: self.call(self.on_selection_cleared)
        self._listing.on_source_removed = lambda path: self.call(self.on_source_removed, path)
        self._listing.on_folder_removed = lambda path: self.call(self.on_folder_removed, path)
        self._listing.on_source_played = lambda path: self.call(self.on_source_played, path)
        self._listing.on_source_dropped_on_source = lambda path, target: self.call(
            self.on_source_dropped_on_source, path, target
        )
        self._listing.on_source_dropped_on_level = lambda path, position: self.call(
            self.on_source_dropped_on_level, path, position
        )
        self._listing.on_menu_requested = self._show_menu

        self._menus.on_source_played = lambda path: self.call(self.on_source_played, path)
        self._menus.on_source_removed = lambda path: self.call(self.on_source_removed, path)
        self._menus.on_source_moved = lambda path, offset: self.call(self.on_source_moved, path, offset)
        self._menus.on_source_level_joined = lambda path, offset: self.call(self.on_source_level_joined, path, offset)
        self._menus.on_source_isolated = lambda path: self.call(self.on_source_isolated, path)
        self._menus.on_folder_removed = lambda path: self.call(self.on_folder_removed, path)
        self._menus.on_folder_toggled = self._toggle_folder

    def _show_menu(self, key: str) -> None:
        """The moves a menu offers follow the run being set up, which decides what a move means."""
        self._menus.show(key, banded=self._banded)

    def _toggle_folder(self, root: Path) -> None:
        """Whether a folder stands open is the list's own memory, so the menu asks the list."""
        self.stems_list.toggle_folder(str(root))
