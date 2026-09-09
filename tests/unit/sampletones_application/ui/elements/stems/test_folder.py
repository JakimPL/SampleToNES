from pathlib import Path
from typing import Any, Callable, Final, FrozenSet, Iterator, List, Optional, Tuple
from unittest.mock import patch

import dearpygui.dearpygui as dpg
import pytest

from sampletones_application.categories.manager import LanguageManager
from sampletones_application.constants.sources import SourceKind
from sampletones_application.layout.config import LayoutConfig
from sampletones_application.layout.loader import load_layout_config
from sampletones_application.paths import (
    BEHAVIOR_DIRECTORY,
    LANG_EN,
    LAYOUT_DIRECTORY,
    PALETTES_DIRECTORY,
    THEME_DIRECTORY,
)
from sampletones_application.tags.compose import compose_tag
from sampletones_application.tags.general import (
    SUF_BUTTON,
    SUF_GROUP,
    SUF_LEAD,
    SUF_TEXT,
    SUF_TWISTY,
    TAG_GLOBAL_THEME_STEMS_GRID,
    TAG_GLOBAL_THEME_STEMS_GROUP_ROW,
    TAG_GLOBAL_THEME_STEMS_MARKER,
)
from sampletones_application.ui.elements.fonts.font import Font
from sampletones_application.ui.elements.fonts.registry import FontRegistry
from sampletones_application.ui.elements.status import GUIStatusBar
from sampletones_application.ui.elements.stems.columns import COLUMN_BORDER, StemsColumns
from sampletones_application.ui.elements.stems.list import GUIStemsList
from sampletones_application.ui.elements.stems.offer import GATHERED_SOURCES
from sampletones_application.ui.elements.stems.tags import StemsTags
from sampletones_application.ui.themes.registry import ThemeRegistry
from sampletones_application.ui.themes.setup import setup_themes
from sampletones_application.utils.palette.catalog import PaletteCatalog
from sampletones_application.utils.palette.source import PaletteSource
from sampletones_application.view_model.shared.stems import (
    StemRowViewModel,
    StemsListViewModel,
)
from sampletones_core.constants.enums import ChannelName
from tests.suite.base import BaseTestSuite
from tests.suite.frames import Frames
from tests.suite.gestures import DOUBLE_CLICKED, click_row_name

ROOT_TAG = "test_root"
PREFIX = "test.stems"
TAGS: Final[StemsTags] = StemsTags(prefix=PREFIX)
CHANNELS: Tuple[ChannelName, ...] = (ChannelName.PULSE1, ChannelName.TRIANGLE)
DEEP_FOLDER: Final[int] = 200
STANDING_OFFSET: Final[float] = 700.0
GLYPH_SIZE: Final[List[float]] = [9.0, 20.0]
NO_OFFSET: Final[float] = 0.0
ROW_PITCH: Final[float] = 20.0
HEADING_HEIGHT: Final[float] = 24.0
REACHED_HELD: Final[int] = 40
FRAMES_TO_FOLLOW: Final[int] = 2
FRAMES_TO_SETTLE: Final[int] = 3
FIRST_HELD: Final[int] = 0
HOLDS_ONE_PAST_THE_CEILING: Final[int] = 13


@pytest.fixture
def layout_config() -> LayoutConfig:
    source = PaletteSource(PaletteCatalog.load(PALETTES_DIRECTORY).default)
    return load_layout_config(LAYOUT_DIRECTORY, BEHAVIOR_DIRECTORY, source)


@pytest.fixture
def dpg_context(layout_config: LayoutConfig) -> Iterator[None]:
    """Stands up the context, fonts and themes the list binds while it draws."""
    dpg.create_context()
    FontRegistry.setup(layout_config.fonts)
    FontRegistry.register_fonts(layout_config.fonts.scale)
    setup_themes(THEME_DIRECTORY, PaletteSource(PaletteCatalog.load(PALETTES_DIRECTORY).default))
    try:
        yield
    finally:
        ThemeRegistry.clear()
        dpg.destroy_context()


@pytest.fixture
def stems_list(dpg_context: None, layout_config: LayoutConfig) -> GUIStemsList:
    """A converter's list of gathered sources, drawn into a window of its own."""
    built = GUIStemsList(
        prefix=PREFIX,
        layout=layout_config.general.stems,
        ceiling=layout_config.general.stems.well_ceiling,
        glyphs=layout_config.glyphs.common,
        language_manager=LanguageManager(LANG_EN),
        status_bar=GUIStatusBar(),
        offer=GATHERED_SOURCES,
    )
    with dpg.window(tag=ROOT_TAG):
        built.create(ROOT_TAG)

    return built


def recording(path: Path, *, channels: FrozenSet[ChannelName] = frozenset(CHANNELS)) -> StemRowViewModel:
    return StemRowViewModel(
        key=str(path),
        kind=SourceKind.RECORDING,
        path=path,
        held=(),
        channels=channels,
        partial_channels=frozenset(),
        bends=frozenset(),
        offered_channels=frozenset(CHANNELS),
        available=True,
        level=0,
        position=0,
        level_size=1,
        level_count=1,
    )


def folder(name: str, *, holds: int) -> StemRowViewModel:
    root = Path(f"/audio/{name}")
    return StemRowViewModel(
        key=str(root),
        kind=SourceKind.FOLDER,
        path=root,
        held=tuple(recording(root / f"take_{index}.wav") for index in range(holds)),
        channels=frozenset(CHANNELS),
        partial_channels=frozenset(),
        bends=frozenset(),
        offered_channels=frozenset(CHANNELS),
        available=True,
        level=0,
        position=0,
        level_size=1,
        level_count=1,
    )


def view(*rows: StemRowViewModel, selected_key: Optional[str] = None) -> StemsListViewModel:
    return StemsListViewModel(
        rows=rows,
        channels_in_play=CHANNELS,
        muted_channels=frozenset(),
        picked_keys=frozenset(),
        picking_room=None,
        live=True,
        collapse_levels=True,
        selected_key=selected_key,
    )


def named(name: str, *, holds: int) -> str:
    """How a folder's row reads: its own name, and how many recordings it holds."""
    return str(LanguageManager(LANG_EN)["global.stems.template.folder_row"].format(name=name, count=holds))


def measured(size: List[float]) -> object:
    """What DearPyGui answers a text measurement with, which needs a drawn frame to be a size."""
    return patch.object(dpg, "get_text_size", return_value=size)


def placed(rows: int) -> Any:
    """Stands in for a frame having placed this many rows of one height under a region's heading.

    A region reads what a row takes from the block its rows were drawn into, which no suite
    renders, so every region answers as the frame would have left it.
    """

    def sized(item: str, *_args: Any, **_kwargs: Any) -> List[float]:
        block = rows * ROW_PITCH + HEADING_HEIGHT
        return [0.0, HEADING_HEIGHT if str(item).endswith(f".{SUF_LEAD}") else block]

    return patch.object(dpg, "get_item_rect_size", side_effect=sized)


def press(tag: str) -> None:
    """Press a widget the way DearPyGui would, with the user data it carries."""
    dpg.get_item_callback(tag)(tag, None, dpg.get_item_user_data(tag))


def twisty_of(row: StemRowViewModel) -> str:
    return TAGS.row(row.key, SUF_TWISTY)


def region_of(row: StemRowViewModel) -> str:
    return TAGS.region(row.key)


def name_of(row: StemRowViewModel) -> str:
    return TAGS.row(row.key, SUF_TEXT)


def box_of(row: StemRowViewModel, channel_name: ChannelName) -> str:
    return TAGS.channel(row.key, channel_name)


def table_of(row: StemRowViewModel) -> int:
    """The grid one row stands in, which is what says whether two rows share a rhythm."""
    return dpg.get_item_parent(TAGS.row(row.key, SUF_GROUP))


def theme_on(row: StemRowViewModel) -> str:
    """The theme one row's line carries, which is what bands a group apart from its neighbors."""
    return dpg.get_item_alias(dpg.get_item_theme(TAGS.row(row.key, SUF_GROUP)))


def folder_without(row: StemRowViewModel, leaving: StemRowViewModel) -> StemRowViewModel:
    """The folder as the model leaves it once one of its recordings is taken out."""
    held = tuple(standing for standing in row.held if standing.key != leaving.key)
    return row.model_copy(update={"held": held})


class TestAClosedFolder(BaseTestSuite):
    """A folder arrives closed, standing as one row that names how many recordings it brought in."""

    def test_it_draws_no_region(self, stems_list: GUIStemsList) -> None:
        sources = folder("sources", holds=3)
        stems_list.update_view(view(sources))
        assert not dpg.does_item_exist(region_of(sources))

    def test_it_draws_none_of_the_recordings_it_holds(self, stems_list: GUIStemsList) -> None:
        sources = folder("sources", holds=3)
        stems_list.update_view(view(sources))
        for held in sources.held:
            assert not dpg.does_item_exist(name_of(held))

    def test_it_carries_a_marker_to_open_it_by(self, stems_list: GUIStemsList) -> None:
        sources = folder("sources", holds=3)
        stems_list.update_view(view(sources))
        assert dpg.does_item_exist(twisty_of(sources))

    def test_a_recording_carries_no_marker(self, stems_list: GUIStemsList) -> None:
        bass = recording(Path("/audio/bass.wav"))
        stems_list.update_view(view(folder("sources", holds=1), bass))
        assert not dpg.does_item_exist(twisty_of(bass))


class TestOpeningAFolder(BaseTestSuite):
    """The marker beside a folder's name puts its recordings in view, and puts them away again."""

    def test_the_marker_opens_a_region(self, stems_list: GUIStemsList) -> None:
        sources = folder("sources", holds=3)
        stems_list.update_view(view(sources))
        press(twisty_of(sources))
        assert dpg.does_item_exist(region_of(sources))

    def test_an_open_folder_draws_the_recordings_it_holds(self, stems_list: GUIStemsList) -> None:
        sources = folder("sources", holds=3)
        stems_list.update_view(view(sources))
        press(twisty_of(sources))
        for held in sources.held:
            assert dpg.does_item_exist(name_of(held))

    def test_the_marker_closes_it_again(self, stems_list: GUIStemsList) -> None:
        sources = folder("sources", holds=3)
        stems_list.update_view(view(sources))
        press(twisty_of(sources))
        press(twisty_of(sources))
        assert not dpg.does_item_exist(region_of(sources))
        assert not dpg.does_item_exist(name_of(sources.held[0]))

    def test_the_folder_row_stands_through_it(self, stems_list: GUIStemsList) -> None:
        sources = folder("sources", holds=3)
        stems_list.update_view(view(sources))
        press(twisty_of(sources))
        assert dpg.does_item_exist(name_of(sources))

    def test_folders_open_apart(self, stems_list: GUIStemsList) -> None:
        first = folder("loops", holds=2)
        second = folder("drums", holds=2)
        stems_list.update_view(view(first, second))
        press(twisty_of(first))
        assert dpg.does_item_exist(region_of(first))
        assert not dpg.does_item_exist(region_of(second))

    def test_a_folder_stays_open_across_a_new_reading(self, stems_list: GUIStemsList) -> None:
        sources = folder("sources", holds=3)
        stems_list.update_view(view(sources))
        press(twisty_of(sources))
        stems_list.update_view(view(sources))
        assert dpg.does_item_exist(region_of(sources))


class TestARecordingInsideAFolder(BaseTestSuite):
    """A reader who opened a folder answers for one of its recordings without leaving the list."""

    def test_it_draws_a_box_on_every_channel_it_offers(self, stems_list: GUIStemsList) -> None:
        sources = folder("sources", holds=2)
        stems_list.update_view(view(sources))
        press(twisty_of(sources))
        for channel_name in CHANNELS:
            assert dpg.does_item_exist(box_of(sources.held[0], channel_name))

    def test_its_box_reports_the_recording_it_belongs_to(self, stems_list: GUIStemsList) -> None:
        sources = folder("sources", holds=2)
        settled: List[Tuple[str, FrozenSet[ChannelName]]] = []
        stems_list.on_channels_changed = lambda key, channels: settled.append((key, channels))

        stems_list.update_view(view(sources))
        press(twisty_of(sources))
        held = sources.held[0]
        box = box_of(held, ChannelName.PULSE1)
        dpg.set_value(box, False)
        dpg.get_item_callback(box)(box, False, dpg.get_item_user_data(box))

        assert settled == [(held.key, frozenset({ChannelName.TRIANGLE}))]


class TestThePickInsideAFolder(BaseTestSuite):
    """A key press acts on the row picked out, which a folder standing open is where one is drawn."""

    def test_a_recording_the_folder_shows_is_the_row_a_key_acts_on(self, stems_list: GUIStemsList) -> None:
        sources = folder("sources", holds=2)
        held = sources.held[FIRST_HELD]

        stems_list.update_view(view(sources, selected_key=held.key))
        press(twisty_of(sources))

        assert stems_list.picked_key == held.key

    def test_closing_the_folder_leaves_no_row_for_a_key_to_act_on(self, stems_list: GUIStemsList) -> None:
        """The reading still names the recording, and the list has taken its widgets away with the
        folder, so a key press has nothing on screen to act on."""
        sources = folder("sources", holds=2)
        held = sources.held[FIRST_HELD]

        stems_list.update_view(view(sources, selected_key=held.key))
        press(twisty_of(sources))
        press(twisty_of(sources))

        assert stems_list.picked_key is None


class TestDoubleClick(BaseTestSuite):
    """A double-click opens what it landed on: a folder shows what it holds, a recording sounds."""

    def test_a_double_clicked_folder_opens(self, stems_list: GUIStemsList) -> None:
        sources = folder("sources", holds=2)
        stems_list.update_view(view(sources))
        double_click(sources)
        assert dpg.does_item_exist(region_of(sources))

    def test_a_double_clicked_recording_is_reported(self, stems_list: GUIStemsList) -> None:
        bass = recording(Path("/audio/bass.wav"))
        opened: List[str] = []
        stems_list.on_row_opened = opened.append

        stems_list.update_view(view(bass))
        double_click(bass)

        assert opened == [bass.key]

    def test_a_double_clicked_folder_sounds_nothing(self, stems_list: GUIStemsList) -> None:
        sources = folder("sources", holds=2)
        opened: List[str] = []
        stems_list.on_row_opened = opened.append

        stems_list.update_view(view(sources))
        double_click(sources)

        assert opened == []


class TestAFolderThatLeaves(BaseTestSuite):
    """A folder taken out of the list is forgotten with it, so its name arriving again is closed."""

    def test_a_folder_that_left_the_list_comes_back_closed(self, stems_list: GUIStemsList) -> None:
        sources = folder("sources", holds=2)
        stems_list.update_view(view(sources))
        press(twisty_of(sources))
        stems_list.update_view(view())
        stems_list.update_view(view(sources))
        assert not dpg.does_item_exist(region_of(sources))


def double_click(row: StemRowViewModel) -> None:
    """Double-click one row's name the way DearPyGui reports the gesture."""
    click_row_name(TAGS, row.key, kind=DOUBLE_CLICKED, button=dpg.mvMouseButton_Left)


class TestARecordingThatLeavesAFolder(BaseTestSuite):
    """A recording taken out from inside an open folder leaves it the way a loose one leaves."""

    @staticmethod
    def _opened(stems_list: GUIStemsList, sources: StemRowViewModel) -> None:
        stems_list.update_view(view(sources))
        press(twisty_of(sources))

    def test_its_remove_button_is_live(self, stems_list: GUIStemsList) -> None:
        sources = folder("sources", holds=3)
        self._opened(stems_list, sources)

        button = TAGS.row(sources.held[0].key, SUF_BUTTON)

        assert dpg.get_item_configuration(button)["enabled"] is True

    def test_one_of_them_leaving_draws_the_folder_again(self, stems_list: GUIStemsList) -> None:
        """The region holds a row apiece, so it is built afresh once the folder holds one fewer."""
        sources = folder("sources", holds=3)
        self._opened(stems_list, sources)
        leaving = sources.held[0]

        stems_list.update_view(view(folder_without(sources, leaving)))

        assert not dpg.does_item_exist(name_of(leaving))

    def test_the_ones_that_stay_are_still_drawn(self, stems_list: GUIStemsList) -> None:
        sources = folder("sources", holds=3)
        self._opened(stems_list, sources)
        leaving = sources.held[0]

        stems_list.update_view(view(folder_without(sources, leaving)))

        for held in sources.held[1:]:
            assert dpg.does_item_exist(name_of(held))

    def test_the_rows_around_the_folder_keep_the_widgets_they_stand_as(self, stems_list: GUIStemsList) -> None:
        """A recording leaving a folder is answered inside it, so the list around it stands."""
        sources = folder("sources", holds=3)
        bass = recording(Path("/audio/bass.wav"))
        stems_list.update_view(view(bass, sources))
        press(twisty_of(sources))
        standing = dpg.get_alias_id(name_of(bass))

        stems_list.update_view(view(bass, folder_without(sources, sources.held[0])))

        assert dpg.get_alias_id(name_of(bass)) == standing

    def test_the_folder_row_keeps_the_widget_it_stands_as(self, stems_list: GUIStemsList) -> None:
        sources = folder("sources", holds=3)
        self._opened(stems_list, sources)
        standing = dpg.get_alias_id(name_of(sources))

        stems_list.update_view(view(folder_without(sources, sources.held[0])))

        assert dpg.get_alias_id(name_of(sources)) == standing

    def test_the_folder_reads_out_how_many_it_now_holds(self, stems_list: GUIStemsList) -> None:
        sources = folder("sources", holds=3)
        self._opened(stems_list, sources)

        stems_list.update_view(view(folder_without(sources, sources.held[0])))

        assert dpg.get_item_label(name_of(sources)) == named("sources", holds=2)

    def test_a_closed_folder_reads_out_how_many_it_now_holds(self, stems_list: GUIStemsList) -> None:
        sources = folder("sources", holds=3)
        stems_list.update_view(view(sources))

        stems_list.update_view(view(folder_without(sources, sources.held[0])))

        assert dpg.get_item_label(name_of(sources)) == named("sources", holds=2)

    @staticmethod
    def _settled(stems_list: GUIStemsList, frames: Frames, *, holds: int) -> StemRowViewModel:
        """An open folder standing at the height its recordings ask for, as a run of frames leaves it.

        A region reads what it holds back the frame after the rows are placed and sizes itself to
        that, so the readings settle over the first few frames and the folder stands still from
        there on.
        """
        sources = folder("sources", holds=holds)
        stems_list.update_view(view(sources))
        press(twisty_of(sources))
        for _ in range(FRAMES_TO_SETTLE):
            with placed(holds):
                frames.render()

        assert frames.pending == 0
        return sources

    def test_one_of_them_leaving_asks_for_the_frame_that_reads_the_folder_back(
        self,
        stems_list: GUIStemsList,
        frames: Frames,
    ) -> None:
        """The region is filled again where the recording stood, so what room its rows now ask for
        is read back once the frame that placed them has been rendered."""
        sources = self._settled(stems_list, frames, holds=HOLDS_ONE_PAST_THE_CEILING)

        stems_list.update_view(view(folder_without(sources, sources.held[FIRST_HELD])))

        assert frames.pending == 1

    def test_the_folder_comes_down_to_the_room_its_recordings_now_ask_for(
        self,
        stems_list: GUIStemsList,
        frames: Frames,
    ) -> None:
        """A folder whose recordings outgrow its region stands at its ceiling and scrolls them;
        with one fewer they fit, and the frame that reads them back is what stands it at their
        own height again."""
        sources = self._settled(stems_list, frames, holds=HOLDS_ONE_PAST_THE_CEILING)
        assert dpg.get_item_configuration(region_of(sources))["auto_resize_y"] is False

        stems_list.update_view(view(folder_without(sources, sources.held[FIRST_HELD])))
        with placed(HOLDS_ONE_PAST_THE_CEILING - 1):
            frames.render()

        assert dpg.get_item_configuration(region_of(sources))["auto_resize_y"] is True

    def test_a_row_arriving_draws_the_list_again(self, stems_list: GUIStemsList) -> None:
        """A row the list did not hold is met by the tables, so those are what is built again."""
        sources = folder("sources", holds=3)
        stems_list.update_view(view(sources))
        standing = dpg.get_alias_id(name_of(sources))

        stems_list.update_view(view(sources, recording(Path("/audio/bass.wav"))))

        assert dpg.get_alias_id(name_of(sources)) != standing


def taken_down_at(offset: float) -> Callable[[str], float]:
    """How DearPyGui reads a region a rebuild replaces: the one standing reports where the reader
    scrolled it to, and the one built in its place stands at its top."""
    standing = [offset]

    def read(_tag: str) -> float:
        return standing.pop() if standing else NO_OFFSET

    return read


class TestWhereAnOpenFolderStands(BaseTestSuite):
    """A rebuild takes an open folder's region down, and the one built in its place opens on the
    rows the reader had scrolled to."""

    @staticmethod
    def _deep(stems_list: GUIStemsList) -> StemRowViewModel:
        sources = folder("sources", holds=DEEP_FOLDER)
        stems_list.update_view(view(sources))
        press(twisty_of(sources))
        return sources

    def test_a_folder_at_its_top_comes_back_at_its_top(self, stems_list: GUIStemsList) -> None:
        sources = self._deep(stems_list)

        stems_list.update_view(view(sources, recording(Path("/audio/bass.wav"))))

        assert dpg.does_item_exist(name_of(sources.held[0]))

    def test_a_folder_scrolled_into_comes_back_where_it_stood(self, stems_list: GUIStemsList) -> None:
        sources = self._deep(stems_list)

        with patch.object(dpg, "get_y_scroll", taken_down_at(STANDING_OFFSET)):
            stems_list.update_view(view(sources, recording(Path("/audio/bass.wav"))))

        assert not dpg.does_item_exist(name_of(sources.held[0]))

    def test_it_draws_the_recordings_that_position_reaches(self, stems_list: GUIStemsList) -> None:
        sources = self._deep(stems_list)

        with patch.object(dpg, "get_y_scroll", taken_down_at(STANDING_OFFSET)):
            stems_list.update_view(view(sources, recording(Path("/audio/bass.wav"))))

        assert any(dpg.does_item_exist(name_of(held)) for held in sources.held)


class TestTheRhythmAFolderStandsIn(BaseTestSuite):
    """A folder's own row is a row like any other, so the list keeps one rhythm down its length.

    A grid gives every row it holds the same height, and a table of its own would give a folder a
    chrome of its own on top of it. So the folder's row stands in the grid of the rows around it,
    and only the region an open folder opens onto breaks the run.
    """

    def test_a_closed_folder_stands_in_the_grid_of_the_rows_around_it(self, stems_list: GUIStemsList) -> None:
        bass = recording(Path("/audio/bass.wav"))
        sources = folder("sources", holds=3)
        lead = recording(Path("/audio/lead.wav"))

        stems_list.update_view(view(bass, sources, lead))

        assert table_of(sources) == table_of(bass) == table_of(lead)

    def test_the_marker_carries_the_theme_that_centers_its_glyph(self, stems_list: GUIStemsList) -> None:
        """The marker's own theme is what spends no padding around the glyph and centers it, which
        is what holds a folder's row to the height of the rows around it."""
        sources = folder("sources", holds=3)

        stems_list.update_view(view(sources))

        assert dpg.get_item_alias(dpg.get_item_theme(twisty_of(sources))) == TAG_GLOBAL_THEME_STEMS_MARKER

    def test_the_marker_stands_as_tall_as_the_name_it_leads(
        self,
        stems_list: GUIStemsList,
        layout_config: LayoutConfig,
    ) -> None:
        sources = folder("sources", holds=3)

        stems_list.update_view(view(sources))

        marker = dpg.get_item_configuration(twisty_of(sources))
        assert marker["height"] == layout_config.general.stems.name_height
        assert marker["width"] == layout_config.general.stems.twisty_width

    def test_an_open_folder_breaks_the_run_so_its_region_stands_between(self, stems_list: GUIStemsList) -> None:
        bass = recording(Path("/audio/bass.wav"))
        sources = folder("sources", holds=3)
        lead = recording(Path("/audio/lead.wav"))
        stems_list.update_view(view(bass, sources, lead))

        press(twisty_of(sources))

        assert table_of(sources) == table_of(bass)
        assert table_of(lead) != table_of(sources)

    def test_a_folder_closed_again_rejoins_the_run(self, stems_list: GUIStemsList) -> None:
        bass = recording(Path("/audio/bass.wav"))
        sources = folder("sources", holds=3)
        lead = recording(Path("/audio/lead.wav"))
        stems_list.update_view(view(bass, sources, lead))
        press(twisty_of(sources))

        press(twisty_of(sources))

        assert table_of(sources) == table_of(bass) == table_of(lead)


class TestWhereTheNamesOpen(BaseTestSuite):
    """A folder opens at its marker and a recording at that marker's glyph, so they read as one
    column of names however the two kinds of row stand beside each other."""

    @staticmethod
    def _grid(layout_config: LayoutConfig) -> StemsColumns:
        """The columns the list declares for a run of gathered sources holding folders."""
        return StemsColumns(
            layout=layout_config.general.stems,
            channels=CHANNELS,
            master=GATHERED_SOURCES.master_box,
            removable=GATHERED_SOURCES.removal,
            bends=GATHERED_SOURCES.bends,
            folders=True,
        )

    @staticmethod
    def _indent(row: StemRowViewModel) -> int:
        return int(dpg.get_item_configuration(name_of(row))["indent"])

    def test_a_folder_opens_at_its_marker(self, stems_list: GUIStemsList) -> None:
        """The marker leads the row, so the name that follows it opens where the marker ends."""
        sources = folder("sources", holds=3)

        with measured(GLYPH_SIZE):
            stems_list.update_view(view(sources))

        assert self._indent(sources) == 0

    def test_a_recording_beside_it_opens_at_the_marker_s_glyph(
        self,
        stems_list: GUIStemsList,
        layout_config: LayoutConfig,
    ) -> None:
        """A measured glyph puts the name in from the edge, which is what lines the column up."""
        bass = recording(Path("/audio/bass.wav"))

        with measured(GLYPH_SIZE):
            stems_list.update_view(view(folder("sources", holds=1), bass))
            expected = self._grid(layout_config).marker_indent(
                layout_config.glyphs.common.collapsed,
                Font.ICON,
            )

        assert expected > 0
        assert self._indent(bass) == expected


class TestTheOneGridAFolderStandsIn(BaseTestSuite):
    """The room a table outside a folder holds clear is the room that folder's region spends.

    The two are computed apart — one as a column at the end of every table, one as the inset a
    region draws its body at — so the columns line up only while both read one figure.
    """

    def test_the_reserve_is_the_room_the_open_folder_s_region_takes(
        self,
        stems_list: GUIStemsList,
        layout_config: LayoutConfig,
    ) -> None:
        sources = folder("sources", holds=3)
        stems_list.update_view(view(sources))

        press(twisty_of(sources))

        body = compose_tag(region_of(sources), SUF_GROUP)
        inset = -int(dpg.get_item_configuration(body)["width"])
        assert inset == layout_config.general.stems.folder_reserve

    def test_the_strip_a_table_declares_comes_out_the_width_of_that_room(
        self,
        stems_list: GUIStemsList,
        layout_config: LayoutConfig,
    ) -> None:
        """The column ending every table and the inset a region draws at are one figure.

        A column takes its own width plus its cell padding and the rule beside it, so what the
        strip holds clear is what the region beside it spends.
        """
        stems = layout_config.general.stems
        sources = folder("sources", holds=3)
        loose = recording(Path("/audio/bass.wav"))
        stems_list.update_view(view(sources, loose))
        press(twisty_of(sources))

        declared = dpg.get_item_children(table_of(loose), 0)
        strip = int(dpg.get_item_configuration(declared[-1])["init_width_or_weight"])
        body = compose_tag(region_of(sources), SUF_GROUP)

        held_clear = strip + 2 * stems.cell_padding + COLUMN_BORDER
        assert held_clear == -int(dpg.get_item_configuration(body)["width"])


class TestTheBandAGroupReadsBy(BaseTestSuite):
    """A group takes a band of its own behind its row, which is what sets it apart from a recording.

    The band is drawn as the row's background rather than as space around it, so a folder reads
    apart while the list keeps the one rhythm every row stands in.
    """

    def test_a_folder_carries_the_band(self, stems_list: GUIStemsList) -> None:
        sources = folder("sources", holds=3)

        stems_list.update_view(view(sources))

        assert theme_on(sources) == TAG_GLOBAL_THEME_STEMS_GROUP_ROW

    def test_a_recording_carries_none(self, stems_list: GUIStemsList) -> None:
        bass = recording(Path("/audio/bass.wav"))

        stems_list.update_view(view(folder("sources", holds=1), bass))

        assert theme_on(bass) != TAG_GLOBAL_THEME_STEMS_GROUP_ROW

    def test_a_recording_inside_a_folder_carries_none(self, stems_list: GUIStemsList) -> None:
        """What a folder holds are recordings, so the band names the folder alone."""
        sources = folder("sources", holds=3)
        stems_list.update_view(view(sources))

        press(twisty_of(sources))

        assert all(theme_on(held) != TAG_GLOBAL_THEME_STEMS_GROUP_ROW for held in sources.held)


class TestWhatMakesTheBandVisible(BaseTestSuite):
    """A band is a row background, so the grid draws one and states its own rows clear.

    The theme on a folder's row paints nothing unless its table draws row backgrounds at all, and
    every other row would take the default alternation if the grid left it unstated.
    """

    def test_the_grid_draws_row_backgrounds(self, stems_list: GUIStemsList) -> None:
        sources = folder("sources", holds=3)

        stems_list.update_view(view(sources))

        assert dpg.get_item_configuration(table_of(sources))["row_background"] is True

    def test_the_grid_carries_the_theme_that_states_its_own_rows_clear(self, stems_list: GUIStemsList) -> None:
        """Every row would otherwise take DearPyGui's own alternation behind the band."""
        bass = recording(Path("/audio/bass.wav"))

        stems_list.update_view(view(folder("sources", holds=1), bass))

        assert dpg.get_item_alias(dpg.get_item_theme(table_of(bass))) == TAG_GLOBAL_THEME_STEMS_GRID


class TestAFolderFollowingItsReader(BaseTestSuite):
    """An open folder reads its rows back the frame after they are placed, and refills itself.

    A folder answers for its own length inside its region, so a scroll into one is answered there:
    the list settles the folder's region and redraws the rows that position now reaches, leaving
    the list around it alone.
    """

    @staticmethod
    def _opened(stems_list: GUIStemsList) -> StemRowViewModel:
        sources = folder("sources", holds=DEEP_FOLDER)
        stems_list.update_view(view(sources))
        press(twisty_of(sources))
        return sources

    @staticmethod
    def _built(sources: StemRowViewModel) -> int:
        """How many of the folder's recordings stand as widgets, which is the block a frame places."""
        return sum(1 for held in sources.held if dpg.does_item_exist(name_of(held)))

    def test_a_scroll_into_one_brings_the_recordings_it_reaches_in(
        self,
        stems_list: GUIStemsList,
        frames: Frames,
    ) -> None:
        """The folder's own region follows the reader, so the list around it keeps its widgets."""
        sources = self._opened(stems_list)
        with placed(self._built(sources)):
            frames.render()

        with placed(self._built(sources)), patch.object(dpg, "get_y_scroll", return_value=STANDING_OFFSET):
            frames.render(FRAMES_TO_FOLLOW)

        assert dpg.does_item_exist(name_of(sources.held[REACHED_HELD]))
        assert not dpg.does_item_exist(name_of(sources.held[FIRST_HELD]))

    def test_the_folder_s_own_row_stays_where_it_stood(
        self,
        stems_list: GUIStemsList,
        frames: Frames,
    ) -> None:
        """A scroll inside a folder is answered inside it, so the rows around it are left be."""
        sources = self._opened(stems_list)
        with placed(self._built(sources)):
            frames.render()
        standing = dpg.get_alias_id(name_of(sources))

        with placed(self._built(sources)), patch.object(dpg, "get_y_scroll", return_value=STANDING_OFFSET):
            frames.render(FRAMES_TO_FOLLOW)

        assert dpg.get_alias_id(name_of(sources)) == standing
