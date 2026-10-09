from typing import Tuple

import dearpygui.dearpygui as dpg

from automation.dearpygui.bridge import Bridge
from automation.dearpygui.hand import Hand
from automation.dearpygui.items.reading import read_item, read_value
from automation.dearpygui.items.regions import enclosing_regions
from automation.dearpygui.items.texts import read_label
from automation.views.prompts import Prompt
from sampletones_application.tags.general import (
    SUF_BUTTON,
    SUF_CHECKBOX,
    SUF_GROUP,
    SUF_SWATCH,
    SUF_TEXT,
)
from sampletones_application.tags.reconstructions import (
    PRE_RECONSTRUCTION_STEMS,
    TAG_RECONSTRUCTIONS_RECONSTRUCTION_CHECKBOX_COLLAPSE_LEVELS,
    TAG_RECONSTRUCTIONS_RECONSTRUCTION_DIALOG_REMOVE_STEM_CONFIRMATION,
)
from sampletones_application.ui.elements.stems.tags import StemsTags


class StemsCard:
    """The Stems card of the Reconstructions tab: a row per recording of the open reconstruction.

    A row is known by the key the card gives its recording, which is the recording's number in
    the reconstruction. The card is the last of its column, so a gesture on a row first scrolls the
    column to its end, as a person scrolls down to it.
    """

    def __init__(
        self,
        bridge: Bridge,
        hand: Hand,
    ) -> None:
        self._bridge = bridge
        self._hand = hand
        self.tags = StemsTags(prefix=PRE_RECONSTRUCTION_STEMS)
        self.remove_prompt = Prompt(
            bridge,
            hand,
            TAG_RECONSTRUCTIONS_RECONSTRUCTION_DIALOG_REMOVE_STEM_CONFIRMATION,
        )

    def levels_collapsed(self) -> bool:
        """Whether the Collapse levels box stands ticked, which folds the level headings away."""
        return bool(self._bridge.ask(lambda: read_value(TAG_RECONSTRUCTIONS_RECONSTRUCTION_CHECKBOX_COLLAPSE_LEVELS)))

    def toggle_levels(self) -> None:
        """Clicks the Collapse levels box, which folds the level headings away or brings them back."""
        self._hand.scroll_into_view(TAG_RECONSTRUCTIONS_RECONSTRUCTION_CHECKBOX_COLLAPSE_LEVELS)
        self._hand.click(TAG_RECONSTRUCTIONS_RECONSTRUCTION_CHECKBOX_COLLAPSE_LEVELS)

    def has_row(self, key: str) -> bool:
        """Whether a row for the recording ``key`` stands on the screen."""
        reading = self._bridge.ask(lambda: read_item(self.tags.row(key, SUF_GROUP)))
        return reading.exists and reading.shown

    def name(self, key: str) -> str:
        """The name the row of ``key`` shows."""
        return self._bridge.ask(lambda: read_label(self.tags.row(key, SUF_TEXT)))

    def is_highlighted(self, key: str) -> bool:
        """Whether the row's name stands highlighted, as a picked row does."""
        return bool(self._bridge.ask(lambda: read_value(self.tags.row(key, SUF_TEXT))))

    def swatch(self, key: str) -> Tuple[float, ...]:
        """The color the row's swatch is filled with."""
        return tuple(
            float(part)
            for part in self._bridge.ask(lambda: dpg.get_item_configuration(self.tags.row(key, SUF_SWATCH))["fill"])
        )

    def can_remove(self, key: str) -> bool:
        """Whether the row's remove button answers."""
        return self._bridge.ask(lambda: read_item(self.tags.row(key, SUF_BUTTON))).enabled

    def remove(self, key: str) -> None:
        """Clicks the row's remove button, which asks first."""
        self._hand.click(self._in_view(self.tags.row(key, SUF_BUTTON)))

    def click(self, key: str) -> None:
        """Clicks the name of the row of ``key``, which picks it."""
        self._hand.click(self._in_view(self.tags.row(key, SUF_TEXT)))

    def reveal(self, key: str) -> None:
        """Double-clicks the row's name, which shows its recording in the file manager."""
        self._hand.double_click(self._in_view(self.tags.row(key, SUF_TEXT)))

    def hears(self, key: str) -> bool:
        """Whether the row's box stands ticked, which is whether its recording is heard."""
        return bool(self._bridge.ask(lambda: read_value(self.tags.row(key, SUF_CHECKBOX))))

    def tick(self, key: str) -> None:
        """Clicks the box of the row of ``key``, which flips whether its recording is heard."""
        self._hand.click(self._in_view(self.tags.row(key, SUF_CHECKBOX)))

    def _in_view(self, item: str) -> str:
        """Scrolls the column the card stands in to its end and ``item`` into view, and returns ``item``."""
        column = self._bridge.ask(lambda: enclosing_regions(self.tags.well))[-1]
        self._hand.scroll_to_end(column)
        self._hand.scroll_into_view(item)
        return item
