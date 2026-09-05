from pathlib import Path
from typing import Final, FrozenSet, Iterator, List, Tuple

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
from sampletones_application.tags.general import SUF_CHANNELS, SUF_CHECKBOX, SUF_TEXT, SUF_TWISTY
from sampletones_application.ui.elements.fonts.registry import FontRegistry
from sampletones_application.ui.elements.status import GUIStatusBar
from sampletones_application.ui.elements.stems.list import GUIStemsList
from sampletones_application.ui.elements.stems.offer import GATHERED_SOURCES
from sampletones_application.ui.themes.registry import ThemeRegistry
from sampletones_application.ui.themes.setup import setup_themes
from sampletones_application.utils.palette.catalog import PaletteCatalog
from sampletones_application.utils.palette.source import PaletteSource
from sampletones_application.view_model.shared.stems import (
    StemRowViewModel,
    StemsListViewModel,
)
from sampletones_core.constants.enums import ChannelName

ROOT_TAG = "test_root"
PREFIX = "test.stems"
CHANNELS: Tuple[ChannelName, ...] = (ChannelName.PULSE1, ChannelName.TRIANGLE)
DOUBLE_CLICK_HANDLER: Final[str] = "mvAppItemType::mvDoubleClickedHandler"


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
        offered_channels=frozenset(CHANNELS),
        available=True,
        level=0,
        position=0,
        level_size=1,
        level_count=1,
    )


def view(*rows: StemRowViewModel) -> StemsListViewModel:
    return StemsListViewModel(
        rows=rows,
        channels_in_play=CHANNELS,
        muted_channels=frozenset(),
        live=True,
        collapse_levels=True,
        selected_key=None,
    )


def press(tag: str) -> None:
    """Press a widget the way DearPyGui would, with the user data it carries."""
    dpg.get_item_callback(tag)(tag, None, dpg.get_item_user_data(tag))


def twisty_of(row: StemRowViewModel) -> str:
    return f"{PREFIX}.row.{row.key}.{SUF_TWISTY}"


def region_of(row: StemRowViewModel) -> str:
    return f"{PREFIX}.folder.{row.key}.region"


def name_of(row: StemRowViewModel) -> str:
    return f"{PREFIX}.row.{row.key}.{SUF_TEXT}"


def box_of(row: StemRowViewModel, channel_name: ChannelName) -> str:
    return f"{PREFIX}.row.{row.key}.{SUF_CHANNELS}.{channel_name}.{SUF_CHECKBOX}"


class TestAClosedFolder:
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


class TestOpeningAFolder:
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


class TestARecordingInsideAFolder:
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


class TestDoubleClick:
    """A double-click opens what it landed on: a folder shows what it holds, a recording sounds."""

    def test_a_double_clicked_folder_opens(self, stems_list: GUIStemsList) -> None:
        sources = folder("sources", holds=2)
        stems_list.update_view(view(sources))
        double_click(name_of(sources))
        assert dpg.does_item_exist(region_of(sources))

    def test_a_double_clicked_recording_is_reported(self, stems_list: GUIStemsList) -> None:
        bass = recording(Path("/audio/bass.wav"))
        opened: List[str] = []
        stems_list.on_row_opened = opened.append

        stems_list.update_view(view(bass))
        double_click(name_of(bass))

        assert opened == [bass.key]

    def test_a_double_clicked_folder_sounds_nothing(self, stems_list: GUIStemsList) -> None:
        sources = folder("sources", holds=2)
        opened: List[str] = []
        stems_list.on_row_opened = opened.append

        stems_list.update_view(view(sources))
        double_click(name_of(sources))

        assert opened == []


class TestAFolderThatLeaves:
    """A folder taken out of the list is forgotten with it, so its name arriving again is closed."""

    def test_a_folder_that_left_the_list_comes_back_closed(self, stems_list: GUIStemsList) -> None:
        sources = folder("sources", holds=2)
        stems_list.update_view(view(sources))
        press(twisty_of(sources))
        stems_list.update_view(view())
        stems_list.update_view(view(sources))
        assert not dpg.does_item_exist(region_of(sources))


def double_click(tag: str) -> None:
    """Double-click a widget the way DearPyGui reports it, through the registry its kind shares."""
    registry = f"{PREFIX}.{SUF_TEXT}.handler.registry"
    for handler in dpg.get_item_children(registry, 1):
        if dpg.get_item_info(handler)["type"] == DOUBLE_CLICK_HANDLER:
            dpg.get_item_callback(handler)(handler, (dpg.mvMouseButton_Left, dpg.get_alias_id(tag)))
            return

    raise AssertionError("the list registers no double-click handler")
