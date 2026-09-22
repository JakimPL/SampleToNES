from typing import Callable, FrozenSet, Optional

import dearpygui.dearpygui as dpg

from sampletones_application.categories.manager import LanguageManager
from sampletones_application.ui.elements.context_menu import (
    add_path_menu_items,
    context_menu,
)
from sampletones_application.ui.elements.fonts.font import Font
from sampletones_application.ui.elements.fonts.registry import FontRegistry
from sampletones_application.ui.elements.stems.list import GUIStemsList
from sampletones_application.view_model.shared.stems import StemRowViewModel
from sampletones_core.constants.enums import ChannelName
from sampletones_shared.utils.callbacks import CallbackMixin


class StemsMenu(CallbackMixin):
    """What a right-click on a recording of the open reconstruction offers.

    The recordings are heard the way the boxes on their rows leave them, so the menu names the
    same choices in one place: switching the recording off or back on, and hearing it alone. A
    recording standing on disk adds the file items every file listing offers.
    """

    def __init__(
        self,
        *,
        stems_list: GUIStemsList,
        language_manager: LanguageManager,
    ) -> None:
        self._stems_list = stems_list
        self._language_manager = language_manager
        self._lbl_mute = language_manager["reconstructions.reconstruction.label.stem_mute"]
        self._lbl_unmute = language_manager["reconstructions.reconstruction.label.stem_unmute"]
        self._lbl_solo = language_manager["reconstructions.reconstruction.label.stem_solo"]
        self._lbl_unsolo = language_manager["reconstructions.reconstruction.label.stem_unsolo"]

        self.on_channels_changed: Optional[Callable[[int, FrozenSet[ChannelName]], None]] = None
        self.on_solo_requested: Optional[Callable[[int], None]] = None

    def show(self, key: str) -> None:
        """Offer what the row a gesture landed on can do."""
        row = self._stems_list.row(key)
        if row is None:
            return

        stem_id = int(key)
        with context_menu():
            self._header(row.name)
            self._create_mute(row, stem_id)
            self._create_solo(row, stem_id)
            if row.path is not None:
                add_path_menu_items(self._language_manager, row.path)

    def _create_mute(self, row: StemRowViewModel, stem_id: int) -> None:
        """The item switching the recording off, or back on across every channel it offers."""
        heard = row.takes_part
        dpg.add_menu_item(
            label=self._lbl_mute if heard else self._lbl_unmute,
            enabled=row.offers_channels,
            callback=lambda: self.call(
                self.on_channels_changed,
                stem_id,
                frozenset() if heard else row.offered_channels,
            ),
        )

    def _create_solo(self, row: StemRowViewModel, stem_id: int) -> None:
        """The item hearing the recording alone, or returning to the mix it replaced."""
        dpg.add_menu_item(
            label=self._lbl_unsolo if self._stems_list.soloed(row.key) else self._lbl_solo,
            enabled=row.offers_channels and self._stems_list.holds_several_rows,
            callback=lambda: self.call(self.on_solo_requested, stem_id),
        )

    @staticmethod
    def _header(name: str) -> None:
        """What the menu names above its items: the recording the gesture landed on."""
        header = dpg.add_text(name)
        FontRegistry.bind_to_item(header, Font.MONO_BOLD)
        dpg.add_separator()
