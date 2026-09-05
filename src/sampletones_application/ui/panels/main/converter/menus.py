from pathlib import Path
from typing import Callable, List, Optional, Tuple

import dearpygui.dearpygui as dpg

from sampletones_application.categories.elements.main import (
    ConverterFolderElements,
    ConverterStemMoveElements,
)
from sampletones_application.categories.hierarchy import Page, Panel, TextType
from sampletones_application.categories.manager import LanguageManager
from sampletones_application.ui.elements.context_menu import (
    add_path_menu_items,
    add_play_menu_item,
    context_menu,
)
from sampletones_application.ui.elements.fonts.font import Font
from sampletones_application.ui.elements.fonts.registry import FontRegistry
from sampletones_application.ui.elements.stems.list import GUIStemsList
from sampletones_application.view_model.shared.stems import StemRowViewModel
from sampletones_shared.types.callback import PathCallback, VoidCallback
from sampletones_shared.utils.callbacks import CallbackMixin

LEVEL_ABOVE: int = -1
LEVEL_BELOW: int = 1
POSITION_EARLIER: int = -1
POSITION_LATER: int = 1

PathOffsetCallback = Callable[[Path, int], None]


class ConverterMenus(CallbackMixin):
    """What a right-click on the list offers, which follows the row it landed on.

    A recording is played wherever it is met, so its menu leads with the item the file browser
    leads with, and offers the moves that rearrange a mix while one is being built. A folder
    stands for everything gathered below it, so its menu reaches all of them at once and leaves
    the recordings inside it to their own menus.
    """

    def __init__(
        self,
        *,
        stems_list: GUIStemsList,
        language_manager: LanguageManager,
    ) -> None:
        self._stems_list = stems_list
        self._language_manager = language_manager
        self._lbl_play = language_manager["global.context.label.play"]

        self.on_source_played: Optional[PathCallback] = None
        self.on_source_removed: Optional[PathCallback] = None
        self.on_source_moved: Optional[PathOffsetCallback] = None
        self.on_source_level_joined: Optional[PathOffsetCallback] = None
        self.on_source_isolated: Optional[PathCallback] = None
        self.on_folder_removed: Optional[PathCallback] = None
        self.on_folder_toggled: Optional[PathCallback] = None

    def show(self, key: str, *, banded: bool) -> None:
        """Offer what the row a gesture landed on can do, reading the kind of row it is.

        ``banded`` states that the list is drawing levels, which is what the moves rearrange.
        """
        row = self._stems_list.row(key)
        if row is None:
            return

        if row.stands_for_a_folder:
            self._show_folder(row)
            return

        self._show_row(row, banded=banded)

    def _show_row(self, row: StemRowViewModel, *, banded: bool) -> None:
        with context_menu():
            self._header(row.name)
            add_play_menu_item(
                self._lbl_play,
                lambda: self.call(self.on_source_played, row.path),
                enabled=row.available,
            )
            for element, enabled, callback in self._moves(row, banded=banded):
                dpg.add_menu_item(label=self._label(element), enabled=enabled, callback=callback)

            add_path_menu_items(self._language_manager, row.path)

    def _show_folder(self, row: StemRowViewModel) -> None:
        opened = self._stems_list.stands_open(row.key)
        with context_menu():
            self._header(row.name)
            dpg.add_menu_item(
                label=self._folder_label(
                    ConverterFolderElements.CONTEXT_CLOSE_FOLDER
                    if opened
                    else ConverterFolderElements.CONTEXT_OPEN_FOLDER
                ),
                callback=lambda: self.call(self.on_folder_toggled, row.path),
            )
            dpg.add_menu_item(
                label=self._folder_label(ConverterFolderElements.CONTEXT_REMOVE_FOLDER),
                callback=lambda: self.call(self.on_folder_removed, row.path),
            )
            add_path_menu_items(self._language_manager, row.path)

    def _moves(
        self,
        row: StemRowViewModel,
        *,
        banded: bool,
    ) -> List[Tuple[ConverterStemMoveElements, bool, VoidCallback]]:
        """The moves the row can make, which are the level moves while a mix is banded.

        A run writing a reconstruction apiece has no order to rearrange, so it offers the one move
        that means something there: taking the recording out.
        """
        path = row.path
        removal = (
            ConverterStemMoveElements.CONTEXT_REMOVE_STEM,
            True,
            lambda: self.call(self.on_source_removed, path),
        )
        if not banded:
            return [removal]

        return [
            (
                ConverterStemMoveElements.CONTEXT_MOVE_UP,
                not row.is_first_on_level,
                lambda: self.call(self.on_source_moved, path, POSITION_EARLIER),
            ),
            (
                ConverterStemMoveElements.CONTEXT_MOVE_DOWN,
                not row.is_last_on_level,
                lambda: self.call(self.on_source_moved, path, POSITION_LATER),
            ),
            (
                ConverterStemMoveElements.CONTEXT_JOIN_ABOVE,
                row.has_level_above,
                lambda: self.call(self.on_source_level_joined, path, LEVEL_ABOVE),
            ),
            (
                ConverterStemMoveElements.CONTEXT_JOIN_BELOW,
                row.has_level_below,
                lambda: self.call(self.on_source_level_joined, path, LEVEL_BELOW),
            ),
            (
                ConverterStemMoveElements.CONTEXT_ISOLATE,
                not row.alone_on_level,
                lambda: self.call(self.on_source_isolated, path),
            ),
            removal,
        ]

    @staticmethod
    def _header(name: str) -> None:
        """What the menu names above its items: whatever the gesture landed on."""
        header = dpg.add_text(name)
        FontRegistry.bind_to_item(header, Font.MONO_BOLD)
        dpg.add_separator()

    def _label(self, element: ConverterStemMoveElements) -> str:
        return self._language_manager[Page.MAIN, Panel.CONVERTER, TextType.LABEL, element]

    def _folder_label(self, element: ConverterFolderElements) -> str:
        return self._language_manager[Page.MAIN, Panel.CONVERTER, TextType.LABEL, element]
