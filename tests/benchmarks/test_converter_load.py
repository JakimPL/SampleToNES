from itertools import count
from pathlib import Path
from typing import Callable, Final, Iterator, Tuple

import dearpygui.dearpygui as dpg
import pytest

from sampletones_application.categories.manager import LanguageManager
from sampletones_application.constants.output import OutputKind
from sampletones_application.layout.config import LayoutConfig
from sampletones_application.layout.loader import load_layout_config
from sampletones_application.logic.main.converter.destination import Destination
from sampletones_application.logic.main.converter.gathering import Gathering
from sampletones_application.logic.main.converter.settings import RunSettings
from sampletones_application.logic.main.converter.setup import batch_entries
from sampletones_application.logic.main.converter.state import ConverterState
from sampletones_application.logic.main.converter.view import stem_rows
from sampletones_application.logic.main.sources.folder import Folder
from sampletones_application.logic.main.sources.key import SourceKey
from sampletones_application.logic.main.sources.list import SourceList
from sampletones_application.logic.main.sources.recording import Recording
from sampletones_application.logic.main.sources.slots import CHANNEL_SLOT
from sampletones_application.paths import (
    BEHAVIOR_DIRECTORY,
    LANG_EN,
    LAYOUT_DIRECTORY,
    PALETTES_DIRECTORY,
    THEME_DIRECTORY,
)
from sampletones_application.tags.general import SUF_TEXT
from sampletones_application.ui.elements.fonts.registry import FontRegistry
from sampletones_application.ui.elements.layout.geometry import RowGeometry
from sampletones_application.ui.elements.status import GUIStatusBar
from sampletones_application.ui.elements.stems.gestures import ROW_WIDGET_KINDS
from sampletones_application.ui.elements.stems.list import GUIStemsList
from sampletones_application.ui.elements.stems.offer import GATHERED_SOURCES
from sampletones_application.ui.elements.stems.tags import StemsTags
from sampletones_application.ui.themes.registry import ThemeRegistry
from sampletones_application.ui.themes.setup import setup_themes
from sampletones_application.utils.palette.catalog import PaletteCatalog
from sampletones_application.utils.palette.source import PaletteSource
from sampletones_application.view_model.shared.stems import StemsListViewModel
from sampletones_core.constants.algorithm import DEFAULT_STEMS_HIERARCHY_MODE
from sampletones_core.constants.enums import ChannelName
from sampletones_core.reconstructions.reconstructor.stems.configs.settings import StemSettings
from tests.suite.base import BaseTestSuite
from tests.suite.timing import seconds

SMALL_FOLDER: Final[int] = 1_000
LARGE_FOLDER: Final[int] = 10_000
GROWTH_ALLOWANCE: Final[float] = 2.0
UNREADABLE: Final[float] = float("inf")
SETTINGS: Final[StemSettings] = StemSettings(channels=[ChannelName.PULSE1], bends=[])
SMALL_ROOT: Final[Path] = Path("/gathered/small")
LARGE_ROOT: Final[Path] = Path("/gathered/large")
ROOT_TAG: Final[str] = "load_root"


def folder_of(root: Path, count: int) -> Folder:
    """A gathered folder of ``count`` recordings, each settled the way a fresh one arrives."""
    return Folder(
        root=root,
        recordings=tuple(Recording(path=root / f"{index:06d}.wav", settings=SETTINGS) for index in range(count)),
    )


def gathering_of(root: Path, count: int) -> Gathering:
    """The setup a reader is left with after gathering one folder of ``count`` recordings."""
    return Gathering.empty().listing_folder(folder_of(root, count))


def state_of(root: Path, count: int) -> ConverterState:
    """The setup a per-recording run derives its entries from, one folder gathered into it."""
    return ConverterState(
        settings=RunSettings(
            joining=SETTINGS,
            output=OutputKind.PER_RECORDING,
            channel_cap=len(ChannelName),
            hierarchy_mode=DEFAULT_STEMS_HIERARCHY_MODE,
        ),
        gathering=gathering_of(root, count),
        destination=Destination.unset(),
        selected=None,
    )


def growth(small: Callable[[], object], large: Callable[[], object]) -> Tuple[float, float, str]:
    """What each size costs, and a line naming both readings and the growth between them.

    A clock coarse enough to read the smaller run as nothing at all reports the growth as
    unbounded, so the line prints and the bound fails on the reading rather than on the division.
    """
    one = seconds(small)
    many = seconds(large)
    ratio = many / one if one > 0 else UNREADABLE
    report = (
        f"{SMALL_FOLDER} recordings {one * 1000:.1f} ms, "
        f"{LARGE_FOLDER} recordings {many * 1000:.1f} ms, "
        f"{ratio:.1f}x for {LARGE_FOLDER // SMALL_FOLDER}x the recordings"
    )
    print(report)
    return one, many, report


def linear(one: float) -> float:
    """The most a reading may cost while the work it does still follows the list's length.

    ``GROWTH_ALLOWANCE`` is the room the reading itself takes. The smaller run is the divisor and
    is warmed by whatever ran before it, so the two readings differ in more than the work between
    them. The shapes these bounds are here to catch — the list read again for each row, or once
    per folder standing in it — read fifty times over at ten thousand, so the allowance is wide
    enough for the warmth and narrow enough for those.
    """
    return one * (LARGE_FOLDER / SMALL_FOLDER) * GROWTH_ALLOWANCE


class TestGatheringAFolder(BaseTestSuite):
    """A folder joins the list at the cost of the recordings it brought in.

    The list takes over the loose recordings a folder covers, which asks what already stands
    against what is arriving. Answering that recording by recording would make gathering cost the
    square of what a folder holds, which is the shape this bound catches: at ten thousand it is
    the difference between a moment and a minute.
    """

    def test_it_costs_what_the_recordings_it_holds_cost(self) -> None:
        small = folder_of(SMALL_ROOT, SMALL_FOLDER)
        large = folder_of(LARGE_ROOT, LARGE_FOLDER)
        one, many, report = growth(lambda: SourceList().add_folder(small), lambda: SourceList().add_folder(large))

        assert many < linear(one), report

    def test_a_folder_joining_a_list_that_holds_one_costs_the_same(self) -> None:
        """Gathering a second folder reads what the first holds, which is the O(n²) door."""
        standing = SourceList().add_folder(folder_of(SMALL_ROOT, LARGE_FOLDER))
        small = folder_of(Path("/gathered/second/small"), SMALL_FOLDER)
        large = folder_of(Path("/gathered/second/large"), LARGE_FOLDER)
        one, many, report = growth(lambda: standing.add_folder(small), lambda: standing.add_folder(large))

        assert many < linear(one), report


class TestReadingTheRowsAGestureLeaves(BaseTestSuite):
    """Every gesture reads the gathered sources into the rows the list draws.

    A folder is read down to the recordings it holds, each becoming a row of its own and each
    answered for on the disk, so this is the reading a reader waits through on every click. The
    bound holds it to the length of the list rather than to the list times its channels.
    """

    def test_it_costs_what_the_list_holds(self) -> None:
        small = gathering_of(SMALL_ROOT, SMALL_FOLDER)
        large = gathering_of(LARGE_ROOT, LARGE_FOLDER)
        one, many, report = growth(
            lambda: stem_rows(small, mixes=False),
            lambda: stem_rows(large, mixes=False),
        )

        assert many < linear(one), report

    def test_it_reads_a_row_for_every_recording_a_folder_holds(self) -> None:
        """What the reading costs is what it builds, which is a row apiece and the folder's own."""
        rows = stem_rows(gathering_of(LARGE_ROOT, LARGE_FOLDER), mixes=False)

        assert len(rows) == 1
        assert rows[0].holds == LARGE_FOLDER


class TestReadingWhereEachRecordingIsWritten(BaseTestSuite):
    """Every gesture derives the entries a per-recording run would write.

    Settling the setup follows it to the destination, which builds one entry per gathered recording
    holding a channel and asks the list which folder each was gathered from. So this runs on every
    click beside the row reading, and the bound holds it to the length of the list rather than to
    the list times the folders standing in it.
    """

    def test_it_costs_what_the_list_holds(self) -> None:
        small = state_of(SMALL_ROOT, SMALL_FOLDER)
        large = state_of(LARGE_ROOT, LARGE_FOLDER)
        one, many, report = growth(lambda: batch_entries(small), lambda: batch_entries(large))

        assert many < linear(one), report

    def test_it_writes_an_entry_for_every_recording_a_folder_holds(self) -> None:
        """What the derivation costs is what it builds, which is one entry per recording."""
        entries = batch_entries(state_of(LARGE_ROOT, LARGE_FOLDER))

        assert len(entries) == LARGE_FOLDER
        assert entries[0].base_directory == LARGE_ROOT


class TestSettlingAChannel(BaseTestSuite):
    """One box on a folder settles every recording it stands for.

    A folder answers as one group, so the gesture writes the whole of what it holds. That is work
    the length of the list by design; what the bound catches is a settle that reads the list again
    for each recording it writes.
    """

    def test_it_costs_what_the_folder_holds(self) -> None:
        small = gathering_of(SMALL_ROOT, SMALL_FOLDER).sources
        large = gathering_of(LARGE_ROOT, LARGE_FOLDER).sources
        one, many, report = growth(
            lambda: small.toggled(SourceKey.folder(SMALL_ROOT), CHANNEL_SLOT, ChannelName.TRIANGLE),
            lambda: large.toggled(SourceKey.folder(LARGE_ROOT), CHANNEL_SLOT, ChannelName.TRIANGLE),
        )

        assert many < linear(one), report

    def test_settling_one_recording_inside_a_folder_costs_the_same(self) -> None:
        """A reader who opens a folder answers for one recording in it, and pays for that one."""
        small = gathering_of(SMALL_ROOT, SMALL_FOLDER).sources
        large = gathering_of(LARGE_ROOT, LARGE_FOLDER).sources
        one, many, report = growth(
            lambda: small.toggled(SourceKey.recording(SMALL_ROOT / "000500.wav"), CHANNEL_SLOT, ChannelName.NOISE),
            lambda: large.toggled(SourceKey.recording(LARGE_ROOT / "005000.wav"), CHANNEL_SLOT, ChannelName.NOISE),
        )

        assert many < linear(one), report


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
    with dpg.window(tag=ROOT_TAG):
        yield

    ThemeRegistry.clear()
    dpg.destroy_context()


@pytest.fixture(scope="module")
def small_listing() -> StemsListViewModel:
    return listing_of(SMALL_ROOT, SMALL_FOLDER)


@pytest.fixture(scope="module")
def large_listing() -> StemsListViewModel:
    return listing_of(LARGE_ROOT, LARGE_FOLDER)


def listing_of(root: Path, count: int) -> StemsListViewModel:
    """The reading the panel hands the list after a folder of ``count`` recordings is gathered."""
    return StemsListViewModel(
        rows=stem_rows(Gathering.empty().listing_folder(folder_of(root, count)), mixes=False),
        channels_in_play=tuple(ChannelName.items()),
        muted_channels=frozenset(),
        picked_keys=frozenset(),
        picking_room=None,
        live=True,
        collapse_levels=True,
        selected_key=None,
    )


def list_drawn_as(prefix: str, layout_config: LayoutConfig) -> GUIStemsList:
    """A converter's list of gathered sources, drawn into the window standing open."""
    built = GUIStemsList(
        prefix=prefix,
        layout=layout_config.general.stems,
        ceiling=layout_config.general.stems.well_ceiling,
        glyphs=layout_config.glyphs.common,
        language_manager=LanguageManager(LANG_EN),
        status_bar=GUIStatusBar(),
        offer=GATHERED_SOURCES,
    )
    built.create(ROOT_TAG)
    return built


def cleared(prefix: str, stems_list: GUIStemsList) -> None:
    """Take down everything one drawn list stands as: its own well, and the registries it made."""
    tags = StemsTags(prefix=prefix)
    dpg.delete_item(stems_list.tag)
    for kind in ROW_WIDGET_KINDS:
        dpg.delete_item(tags.handlers(kind))


def rows_on_screen(prefix: str, listing: StemsListViewModel) -> int:
    """How many of a folder's recordings the list put widgets on screen for."""
    folder_row = listing.rows[0]
    tags = StemsTags(prefix=prefix)
    return sum(1 for held in folder_row.held if dpg.does_item_exist(tags.row(held.key, SUF_TEXT)))


class TestDrawingAGatheredFolder(BaseTestSuite):
    """What an open folder builds is what a reader can see, however many recordings it holds.

    The rows outside the window stand as reserved room rather than as widgets, so the interface a
    folder of ten thousand costs is the interface a folder of ten costs. Before a row has been
    measured the region is generous, which is the window this counts against.
    """

    def test_it_builds_what_a_reader_can_see(
        self,
        dpg_context: None,
        layout_config: LayoutConfig,
        small_listing: StemsListViewModel,
        large_listing: StemsListViewModel,
    ) -> None:
        layout = layout_config.general.stems
        window = RowGeometry.unmeasured(overscan=layout.window_overscan).size(float(layout.folder_ceiling))
        drawn = tuple(
            self._opened(prefix, layout_config, listing)
            for prefix, listing in (("load.small", small_listing), ("load.large", large_listing))
        )

        assert drawn == (window, window)

    def test_opening_it_costs_what_a_reader_can_see(
        self,
        dpg_context: None,
        layout_config: LayoutConfig,
        small_listing: StemsListViewModel,
        large_listing: StemsListViewModel,
    ) -> None:
        """The whole gesture, from the reading the panel hands over to the widgets on screen."""
        runs = count()
        one = seconds(lambda: self._opened(f"load.timed.{next(runs)}", layout_config, small_listing))
        many = seconds(lambda: self._opened(f"load.timed.{next(runs)}", layout_config, large_listing))
        report = f"{SMALL_FOLDER} recordings {one * 1000:.1f} ms, {LARGE_FOLDER} recordings {many * 1000:.1f} ms"
        print(report)

        assert many < linear(one), report

    @staticmethod
    def _opened(prefix: str, layout_config: LayoutConfig, listing: StemsListViewModel) -> int:
        """Draw the listing, open the folder standing in it, and count the rows that reached screen.

        What the gesture built is taken down once it has been counted, so a batch of them costs
        what one costs: the window each reading is taken in holds the widgets of that reading
        alone, and the small run is measured on the same window as the large one.
        """
        stems_list = list_drawn_as(prefix, layout_config)
        stems_list.update_view(listing)
        stems_list.toggle_folder(listing.rows[0].key)
        reached = rows_on_screen(prefix, listing)
        cleared(prefix, stems_list)
        return reached
