from dataclasses import dataclass
from typing import Final, List, Tuple

import dearpygui.dearpygui as dpg

from sampletones_application.tags.compose import compose_tag
from sampletones_application.tags.general import SUF_BUTTON
from sampletones_application.tags.sequencer import (
    TAG_SEQUENCER_HISTORY_BUTTON_REDO,
    TAG_SEQUENCER_HISTORY_BUTTON_UNDO,
    TAG_SEQUENCER_HISTORY_WINDOW_LIST,
)
from tests.suite.screens.dearpygui.bridge import Bridge
from tests.suite.screens.dearpygui.hand import Hand
from tests.suite.screens.dearpygui.items.types import TEXT_TYPE, Item

TABLE_TYPE: Final[str] = "mvAppItemType::mvTable"
ENTRY_GROUP: Final[int] = 1
COLOR_KEY: Final[str] = "color"


@dataclass(frozen=True)
class HistorySegment:
    """One piece of a history line: its words and the color they are drawn in."""

    words: str
    color: Tuple[float, ...]


@dataclass(frozen=True)
class HistoryLine:
    """One entry of the History card as it reads: its pieces, and whether it is the state in force."""

    segments: Tuple[HistorySegment, ...]
    current: bool

    @property
    def words(self) -> str:
        """The words of every piece of the line, joined by spaces."""
        return " ".join(segment.words for segment in self.segments)


class History:
    """The History card of the Sequencer: one line per entry, the newest on top, with Undo and Redo below."""

    def __init__(
        self,
        bridge: Bridge,
        hand: Hand,
    ) -> None:
        self._bridge = bridge
        self._hand = hand

    def lines(self) -> Tuple[HistoryLine, ...]:
        """The lines the card draws, newest first."""
        return self._bridge.ask(read_history)

    def current(self) -> HistoryLine:
        """The line of the entry the project stands at."""
        return next(line for line in self.lines() if line.current)

    def undo(self) -> None:
        """Clicks Undo below the list, which steps the project back one entry."""
        self._hand.click(compose_tag(TAG_SEQUENCER_HISTORY_BUTTON_UNDO, SUF_BUTTON))

    def redo(self) -> None:
        """Clicks Redo below the list, which steps the project forward one entry."""
        self._hand.click(compose_tag(TAG_SEQUENCER_HISTORY_BUTTON_REDO, SUF_BUTTON))


def read_history() -> Tuple[HistoryLine, ...]:
    """The lines the History card draws, newest first. Runs on the render thread."""
    tables = [
        child
        for child in dpg.get_item_children(TAG_SEQUENCER_HISTORY_WINDOW_LIST, 1)
        if dpg.get_item_info(child)["type"] == TABLE_TYPE
    ]
    if not tables:
        return ()

    lines: List[HistoryLine] = []
    for row in dpg.get_item_children(tables[0], 1):
        selectable, group = dpg.get_item_children(row, 1)[: ENTRY_GROUP + 1]
        lines.append(HistoryLine(segments=_segments(group), current=bool(dpg.get_value(selectable))))

    return tuple(lines)


def _segments(group: Item) -> Tuple[HistorySegment, ...]:
    """The pieces of one history line, each with its words and color, in the order drawn."""
    return tuple(
        HistorySegment(
            words=str(dpg.get_value(text)),
            color=tuple(float(part) for part in dpg.get_item_configuration(text)[COLOR_KEY]),
        )
        for text in dpg.get_item_children(group, 1)
        if dpg.get_item_info(text)["type"] == TEXT_TYPE
    )
