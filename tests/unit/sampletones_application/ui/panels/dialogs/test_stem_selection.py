from pathlib import Path
from typing import Final, List, Sequence

import dearpygui.dearpygui as dpg
import pytest

from sampletones_application.categories.manager import LanguageManager
from sampletones_application.constants.conversion import MAX_STEM_SOURCES
from sampletones_application.constants.sources import SourceKind
from sampletones_application.layout.config import LayoutConfig
from sampletones_application.paths import LANG_EN
from sampletones_application.tags.compose import compose_tag
from sampletones_application.tags.general import SUF_BUTTON, SUF_CHECKBOX, SUF_ROW
from sampletones_application.tags.main import (
    PRE_MAIN_CONVERTER_CANDIDATE,
    TAG_MAIN_CONVERTER_BUTTON_ADD_STEMS,
    TAG_MAIN_CONVERTER_TEXT_STEM_SELECTION_LIMIT,
)
from sampletones_application.ui.elements.status import GUIStatusBar
from sampletones_application.ui.panels.dialogs.stem_selection import GUIStemSelectionWindow
from sampletones_application.utils.gui.keyboard import KeyRouter
from sampletones_application.view_model.shared.stems import StemRowViewModel
from sampletones_core.constants.enums import ChannelName
from tests.suite.base import BaseTestSuite
from tests.suite.shortcuts import shipped_source

LANGUAGE_MANAGER: Final[LanguageManager] = LanguageManager(LANG_EN)
GATHERED: Final[int] = MAX_STEM_SOURCES + 4


@pytest.fixture(name="window")
def window_fixture(dpg_context: None, layout_config: LayoutConfig) -> GUIStemSelectionWindow:
    return GUIStemSelectionWindow(
        layout=layout_config.tabs.main.converter,
        stems_layout=layout_config.general.stems,
        glyphs=layout_config.glyphs.common,
        language_manager=LANGUAGE_MANAGER,
        status_bar=GUIStatusBar(),
        title=LANGUAGE_MANAGER["main.converter.title.stem_selection_dialog"],
        message=LANGUAGE_MANAGER["main.converter.message.stem_selection_prompt"],
        limit_template=LANGUAGE_MANAGER["main.converter.template.stem_selection_limit"],
        add_label=LANGUAGE_MANAGER["main.converter.label.add_stems_button"],
        cancel_label=LANGUAGE_MANAGER["global.dialog.label.cancel"],
        key_router=KeyRouter(),
        shortcut_source=shipped_source(),
    )


def recording_row(path: Path) -> StemRowViewModel:
    """One gathered recording, as the converter's list draws it."""
    return StemRowViewModel(
        key=str(path),
        kind=SourceKind.RECORDING,
        path=path,
        held=(),
        channels=frozenset({ChannelName.PULSE1}),
        partial_channels=frozenset(),
        offered_channels=frozenset({ChannelName.PULSE1}),
        available=True,
        level=0,
        position=0,
        level_size=1,
        level_count=1,
    )


def folder_row(root: Path, held: Sequence[Path]) -> StemRowViewModel:
    """A gathered folder standing for the recordings below it."""
    return StemRowViewModel(
        key=str(root),
        kind=SourceKind.FOLDER,
        path=root,
        held=tuple(recording_row(path) for path in held),
        channels=frozenset({ChannelName.PULSE1}),
        partial_channels=frozenset(),
        offered_channels=frozenset({ChannelName.PULSE1}),
        available=True,
        level=0,
        position=0,
        level_size=1,
        level_count=1,
    )


def paths(count: int = GATHERED) -> List[Path]:
    return [Path(f"/audio/take_{index}.wav") for index in range(count)]


def candidates(count: int = GATHERED) -> List[StemRowViewModel]:
    return [recording_row(path) for path in paths(count)]


def render(window: GUIStemSelectionWindow, offered: Sequence[StemRowViewModel]) -> None:
    """Builds the widget tree for what was gathered, the way ``open`` does without a live frame."""
    window.open(offered, MAX_STEM_SOURCES)


def box_of(row: StemRowViewModel) -> str:
    return compose_tag(PRE_MAIN_CONVERTER_CANDIDATE, SUF_ROW, row.key, SUF_CHECKBOX)


def pick(row: StemRowViewModel) -> None:
    """Click one row's box the way DearPyGui reports a checkbox."""
    tag = box_of(row)
    dpg.get_item_callback(tag)(tag, not dpg.get_value(tag), dpg.get_item_user_data(tag))


def add_enabled() -> bool:
    return bool(dpg.get_item_configuration(compose_tag(TAG_MAIN_CONVERTER_BUTTON_ADD_STEMS, SUF_BUTTON))["enabled"])


class TestWhatIsOffered(BaseTestSuite):
    """Everything gathered is offered and pickable, with as many as a mix holds arriving ticked."""

    def test_every_recording_gathered_gets_a_box(self, window: GUIStemSelectionWindow) -> None:
        offered = candidates()
        render(window, offered)
        for row in offered:
            assert dpg.does_item_exist(box_of(row))

    def test_the_ones_a_mix_holds_arrive_ticked(self, window: GUIStemSelectionWindow) -> None:
        offered = candidates()
        render(window, offered)
        assert [dpg.get_value(box_of(row)) for row in offered[:MAX_STEM_SOURCES]] == [True] * MAX_STEM_SOURCES

    def test_the_rest_arrive_clear(self, window: GUIStemSelectionWindow) -> None:
        offered = candidates()
        render(window, offered)
        assert not any(dpg.get_value(box_of(row)) for row in offered[MAX_STEM_SOURCES:])

    def test_a_recording_past_the_limit_is_pickable(self, window: GUIStemSelectionWindow) -> None:
        """Swapping which recordings the mix is built from is what the question is for."""
        offered = candidates()
        render(window, offered)
        beyond = offered[MAX_STEM_SOURCES]
        assert dpg.get_item_configuration(box_of(beyond))["enabled"] is True

        pick(beyond)

        assert dpg.get_value(box_of(beyond)) is True


class TestSettlingTheMix(BaseTestSuite):
    """The mix is settled once the pick fits, and the line above says where the pick stands."""

    def test_a_pick_that_fits_settles(self, window: GUIStemSelectionWindow) -> None:
        offered = candidates()
        answered: List[List[Path]] = []
        window.on_add = answered.append

        render(window, offered)
        dpg.get_item_callback(compose_tag(TAG_MAIN_CONVERTER_BUTTON_ADD_STEMS, SUF_BUTTON))()

        assert answered == [paths()[:MAX_STEM_SOURCES]]

    def test_swapping_one_for_another_keeps_it_settling(self, window: GUIStemSelectionWindow) -> None:
        offered = candidates()
        answered: List[List[Path]] = []
        window.on_add = answered.append

        render(window, offered)
        pick(offered[0])
        pick(offered[MAX_STEM_SOURCES])
        dpg.get_item_callback(compose_tag(TAG_MAIN_CONVERTER_BUTTON_ADD_STEMS, SUF_BUTTON))()

        assert answered == [paths()[1 : MAX_STEM_SOURCES + 1]]

    def test_a_pick_larger_than_a_mix_holds_waits(self, window: GUIStemSelectionWindow) -> None:
        offered = candidates()
        answered: List[List[Path]] = []
        window.on_add = answered.append

        render(window, offered)
        pick(offered[MAX_STEM_SOURCES])

        assert add_enabled() is False
        dpg.get_item_callback(compose_tag(TAG_MAIN_CONVERTER_BUTTON_ADD_STEMS, SUF_BUTTON))()
        assert answered == []

    def test_a_pick_of_nothing_waits(self, window: GUIStemSelectionWindow) -> None:
        offered = candidates()
        render(window, offered)
        for row in offered[:MAX_STEM_SOURCES]:
            pick(row)

        assert add_enabled() is False

    def test_letting_one_go_settles_again(self, window: GUIStemSelectionWindow) -> None:
        offered = candidates()
        render(window, offered)
        pick(offered[MAX_STEM_SOURCES])
        assert add_enabled() is False

        pick(offered[0])

        assert add_enabled() is True

    def test_the_line_reads_what_stands_picked(self, window: GUIStemSelectionWindow) -> None:
        offered = candidates()
        render(window, offered)
        opening = dpg.get_value(TAG_MAIN_CONVERTER_TEXT_STEM_SELECTION_LIMIT)

        pick(offered[MAX_STEM_SOURCES])

        assert dpg.get_value(TAG_MAIN_CONVERTER_TEXT_STEM_SELECTION_LIMIT) != opening

    def test_a_list_a_mix_already_holds_arrives_settling(self, window: GUIStemSelectionWindow) -> None:
        offered = candidates(MAX_STEM_SOURCES)
        render(window, offered)
        assert add_enabled() is True


class TestAFolderInTheQuestion(BaseTestSuite):
    """A folder stands as the row it stands as in the card, answering for what it holds."""

    def test_the_folder_stands_as_one_row(self, window: GUIStemSelectionWindow) -> None:
        held = paths(3)
        render(window, [folder_row(Path("/audio/takes"), held)])

        assert dpg.does_item_exist(box_of(folder_row(Path("/audio/takes"), held)))

    def test_it_counts_the_recordings_it_holds(self, window: GUIStemSelectionWindow) -> None:
        """The line above counts recordings, so a folder counts as what it brings in."""
        held = paths(3)
        render(window, [folder_row(Path("/audio/takes"), held)])

        assert "3" in dpg.get_value(TAG_MAIN_CONVERTER_TEXT_STEM_SELECTION_LIMIT)

    def test_one_click_lets_the_whole_folder_go(self, window: GUIStemSelectionWindow) -> None:
        held = paths(3)
        folder = folder_row(Path("/audio/takes"), held)
        render(window, [folder])
        assert dpg.get_value(box_of(folder)) is True

        pick(folder)

        assert add_enabled() is False

    def test_what_it_holds_is_what_the_mix_takes(self, window: GUIStemSelectionWindow) -> None:
        held = paths(3)
        answered: List[List[Path]] = []
        window.on_add = answered.append
        render(window, [folder_row(Path("/audio/takes"), held)])

        dpg.get_item_callback(compose_tag(TAG_MAIN_CONVERTER_BUTTON_ADD_STEMS, SUF_BUTTON))()

        assert answered == [held]
