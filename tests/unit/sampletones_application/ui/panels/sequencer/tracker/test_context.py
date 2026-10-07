from dataclasses import dataclass
from typing import Dict, Final, List, Optional, Tuple

import dearpygui.dearpygui as dpg
import pytest

from sampletones_application.layout.config import LayoutConfig
from sampletones_application.logic.project.controller import ProjectController
from sampletones_application.logic.project.manager import ProjectManager
from sampletones_application.logic.sequencer.tracker import SequencerTrackerLogic
from sampletones_application.tags.sequencer import TAG_SEQUENCER_TRACKER_TABLE
from sampletones_application.ui.panels.sequencer.tracker.band import TrackerRows
from sampletones_application.ui.panels.sequencer.tracker.context import BLANK_LABEL, ContextRows
from sampletones_application.ui.panels.sequencer.tracker.themes import TrackerThemes
from sampletones_application.view_model.sequencer.settings import SequencerSettingsViewModel
from sampletones_application.view_model.sequencer.subcolumn import SubColumn
from sampletones_application.view_model.sequencer.tracker import SequencerTrackerViewModel
from sampletones_core.constants.enums import ChannelName
from sampletones_core.utils.display import display_id, display_volume

FRAME_ROWS: Final[int] = 4
REACH: Final[int] = 3
SONG_REACH: Final[int] = 2
MARKED_VOLUME: Final[int] = 5
BAR: Final[int] = 2
BEAT: Final[int] = 8
PULSE1_VOLUME_SLOT: Final[int] = len(SubColumn) + list(SubColumn).index(SubColumn.VOLUME)


@dataclass(frozen=True, kw_only=True)
class Song:
    """Three frames of :data:`FRAME_ROWS` rows, a volume on the first frame's last row."""

    logic: SequencerTrackerLogic

    def around(self, frame_index: int) -> SequencerTrackerViewModel:
        """The grid of one frame with :data:`SONG_REACH` rows of the song either side of it."""
        self.logic.select_frame(frame_index)
        return self.logic.build_grid()


@pytest.fixture
def song() -> Song:
    controller = ProjectController(ProjectManager())
    controller.set_rows_per_pattern(FRAME_ROWS)
    controller.append_frame()
    controller.append_frame()
    logic = SequencerTrackerLogic(controller)
    logic.set_cell_subcolumn(FRAME_ROWS - 1, ChannelName.PULSE1, volume=MARKED_VOLUME)
    logic.set_reach(SONG_REACH)
    return Song(logic=logic)


@pytest.fixture
def context_rows(layout_config: LayoutConfig, tracker_table: str) -> ContextRows:
    layout = layout_config.tabs.sequencer
    themes = TrackerThemes(layout)
    themes.create()
    return ContextRows(
        layout=layout,
        themes=themes,
        subcolumn_widths={subcolumn: layout.tracker.subcolumn_widths.voice for subcolumn in SubColumn},
    )


def _settings() -> SequencerSettingsViewModel:
    """A meter whose bar opens every :data:`BAR` rows and whose beat never opens inside one."""
    return SequencerSettingsViewModel(
        nes_frequency=60,
        tempo=150,
        speed=6,
        rows_per_pattern=FRAME_ROWS,
        first_highlight=BEAT,
        second_highlight=BAR,
    )


def _table_rows() -> List[int]:
    """The rows the table holds below its header."""
    return list(dpg.get_item_children(TAG_SEQUENCER_TRACKER_TABLE, 1))[1:]


def _numbers() -> List[str]:
    """What the row-number cell of each row below the header reads."""
    numbers: List[str] = []
    for table_row in _table_rows():
        number_cell = dpg.get_item_children(table_row, 1)[1]
        numbers.append(dpg.get_item_configuration(dpg.get_item_children(number_cell, 1)[0])["label"])

    return numbers


def _slots(table_row: int) -> List[int]:
    """Every slot selectable a row lays out, the Sample column's first."""
    slots: List[int] = []
    for cell in dpg.get_item_children(table_row, 1):
        for child in dpg.get_item_children(cell, 1):
            if dpg.get_item_info(child)["type"] == "mvAppItemType::mvGroup":
                slots.extend(dpg.get_item_children(child, 1))

    return slots


def _volume_label(table_row: int) -> str:
    """What the Pulse 1 volume slot of a row reads, the Sample column's three slots standing before it."""
    return str(dpg.get_item_configuration(_slots(table_row)[PULSE1_VOLUME_SLOT])["label"])


class TestTheRowsBeforeTheFrame:
    """The rows above the frame show the song's rows leading into it, blank above where the song begins."""

    def test_the_songs_rows_stand_nearest_the_frame_last(self, context_rows: ContextRows, song: Song) -> None:
        context_rows.build_lead(REACH, song.around(1).lead)

        assert _numbers() == [BLANK_LABEL, display_id(FRAME_ROWS - 2), display_id(FRAME_ROWS - 1)]

    def test_a_row_reads_what_its_own_frame_holds(self, context_rows: ContextRows, song: Song) -> None:
        context_rows.build_lead(REACH, song.around(1).lead)

        assert _volume_label(_table_rows()[-1]) == display_volume(MARKED_VOLUME)

    def test_a_reach_shorter_than_what_the_song_holds_takes_the_nearest(
        self,
        context_rows: ContextRows,
        song: Song,
    ) -> None:
        context_rows.build_lead(1, song.around(1).lead)

        assert _numbers() == [display_id(FRAME_ROWS - 1)]


class TestTheRowsAfterTheFrame:
    """The rows below the frame show the song's rows following it, blank below where the song ends."""

    def test_the_songs_rows_stand_nearest_the_frame_first(self, context_rows: ContextRows, song: Song) -> None:
        context_rows.build_trail(REACH, song.around(1).trail)

        assert _numbers() == [display_id(0), display_id(1), BLANK_LABEL]

    def test_past_the_last_frame_every_row_is_blank(self, context_rows: ContextRows, song: Song) -> None:
        context_rows.build_trail(REACH, song.around(2).trail)

        assert _numbers() == [BLANK_LABEL] * REACH


class TestARowOfAnotherFrameTakesNoGesture:
    """A row beside the frame is read and never edited: its cells answer no click and carry no handler."""

    def test_no_cell_carries_a_callback_or_a_handler(self, context_rows: ContextRows, song: Song) -> None:
        context_rows.build_lead(REACH, song.around(1).lead)

        for table_row in _table_rows():
            for slot in _slots(table_row):
                assert dpg.get_item_configuration(slot)["callback"] is None
                assert dpg.get_item_info(slot)["handlers"] is None


class TestARefill:
    """Showing another frame rewrites the rows standing beside it in place."""

    def test_the_rows_take_the_neighbors_of_the_frame_now_shown(
        self,
        context_rows: ContextRows,
        song: Song,
    ) -> None:
        context_rows.build_lead(REACH, song.around(1).lead)
        context_rows.build_trail(REACH, song.around(1).trail)

        shown = song.around(0)
        context_rows.fill(shown.lead, shown.trail)

        assert _numbers() == [BLANK_LABEL] * REACH + [display_id(0), display_id(1), BLANK_LABEL]


class TestTheShadesBesideTheFrame:
    """A row beside the frame takes its group's shade by its own index, and the mark while it sounds."""

    @staticmethod
    def _shaded(rows: TrackerRows) -> Dict[int, bool]:
        return {
            slot: bool(dpg.is_table_row_highlighted(TAG_SEQUENCER_TRACKER_TABLE, rows.lead_table_row(slot)))
            for slot in range(rows.reach)
        }

    def test_a_row_opening_a_bar_is_shaded_and_a_blank_row_is_not(
        self,
        context_rows: ContextRows,
        song: Song,
    ) -> None:
        rows = TrackerRows(reach=REACH, frame_rows=0)
        context_rows.build_lead(REACH, song.around(1).lead)

        context_rows.paint(rows, _settings(), playing=None)

        assert self._shaded(rows) == {0: False, 1: True, 2: False}

    @pytest.mark.parametrize("playing", [(0, FRAME_ROWS - 1), None])
    def test_the_sounding_row_carries_the_mark(
        self,
        context_rows: ContextRows,
        song: Song,
        playing: Optional[Tuple[int, int]],
    ) -> None:
        rows = TrackerRows(reach=REACH, frame_rows=0)
        context_rows.build_lead(REACH, song.around(1).lead)

        context_rows.paint(rows, _settings(), playing=playing)

        assert self._shaded(rows)[2] is (playing is not None)
