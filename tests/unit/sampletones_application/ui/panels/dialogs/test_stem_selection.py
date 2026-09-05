from pathlib import Path
from typing import Final, List, Sequence

import dearpygui.dearpygui as dpg
import pytest

from sampletones_application.categories.manager import LanguageManager
from sampletones_application.constants.conversion import MAX_STEM_SOURCES
from sampletones_application.layout.config import LayoutConfig
from sampletones_application.paths import LANG_EN
from sampletones_application.tags.compose import compose_tag
from sampletones_application.tags.general import SUF_BUTTON
from sampletones_application.tags.main import (
    PRE_MAIN_CONVERTER_CANDIDATE,
    TAG_MAIN_CONVERTER_BUTTON_ADD_STEMS,
    TAG_MAIN_CONVERTER_TEXT_STEM_SELECTION_LIMIT,
)
from sampletones_application.ui.panels.dialogs.stem_selection import GUIStemSelectionWindow
from sampletones_application.utils.gui.keyboard import KeyRouter
from tests.suite.base import BaseTestSuite
from tests.suite.shortcuts import shipped_source

LANGUAGE_MANAGER: Final[LanguageManager] = LanguageManager(LANG_EN)
GATHERED: Final[int] = MAX_STEM_SOURCES + 4


@pytest.fixture(name="window")
def window_fixture(dpg_context: None, layout_config: LayoutConfig) -> GUIStemSelectionWindow:
    return GUIStemSelectionWindow(
        layout=layout_config.tabs.main.converter,
        title=LANGUAGE_MANAGER["main.converter.title.stem_selection_dialog"],
        message=LANGUAGE_MANAGER["main.converter.message.stem_selection_prompt"],
        limit_template=LANGUAGE_MANAGER["main.converter.template.stem_selection_limit"],
        add_label=LANGUAGE_MANAGER["main.converter.label.add_stems_button"],
        cancel_label=LANGUAGE_MANAGER["global.dialog.label.cancel"],
        key_router=KeyRouter(),
        shortcut_source=shipped_source(),
    )


def candidates(count: int = GATHERED) -> List[Path]:
    return [Path(f"/audio/take_{index}.wav") for index in range(count)]


def render(window: GUIStemSelectionWindow, offered: Sequence[Path]) -> None:
    """Builds the widget tree for what was gathered, the way ``open`` does without a live frame."""
    window.open(offered, MAX_STEM_SOURCES)


def box_of(candidate: Path) -> str:
    return compose_tag(PRE_MAIN_CONVERTER_CANDIDATE, str(candidate))


def pick(candidate: Path, *, picked: bool) -> None:
    """Tick or untick one recording the way DearPyGui reports a checkbox."""
    tag = box_of(candidate)
    dpg.set_value(tag, picked)
    dpg.get_item_callback(tag)(tag, picked, dpg.get_item_user_data(tag))


def add_enabled() -> bool:
    return bool(dpg.get_item_configuration(compose_tag(TAG_MAIN_CONVERTER_BUTTON_ADD_STEMS, SUF_BUTTON))["enabled"])


class TestWhatIsOffered(BaseTestSuite):
    """Everything gathered is offered and pickable, with as many as a mix holds arriving ticked."""

    def test_every_recording_gathered_gets_a_box(self, window: GUIStemSelectionWindow) -> None:
        offered = candidates()
        render(window, offered)
        for candidate in offered:
            assert dpg.does_item_exist(box_of(candidate))

    def test_the_ones_a_mix_holds_arrive_ticked(self, window: GUIStemSelectionWindow) -> None:
        offered = candidates()
        render(window, offered)
        assert [dpg.get_value(box_of(candidate)) for candidate in offered[:MAX_STEM_SOURCES]] == [
            True
        ] * MAX_STEM_SOURCES

    def test_the_rest_arrive_clear(self, window: GUIStemSelectionWindow) -> None:
        offered = candidates()
        render(window, offered)
        assert not any(dpg.get_value(box_of(candidate)) for candidate in offered[MAX_STEM_SOURCES:])

    def test_a_recording_past_the_limit_is_pickable(self, window: GUIStemSelectionWindow) -> None:
        """Swapping which recordings the mix is built from is what the question is for."""
        offered = candidates()
        render(window, offered)
        beyond = offered[MAX_STEM_SOURCES]
        assert dpg.get_item_configuration(box_of(beyond))["enabled"] is True

        pick(beyond, picked=True)

        assert dpg.get_value(box_of(beyond)) is True


class TestSettlingTheMix(BaseTestSuite):
    """The mix is settled once the pick fits, and the line above says where the pick stands."""

    def test_a_pick_that_fits_settles(self, window: GUIStemSelectionWindow) -> None:
        offered = candidates()
        answered: List[List[Path]] = []
        window.on_add = answered.append

        render(window, offered)
        dpg.get_item_callback(compose_tag(TAG_MAIN_CONVERTER_BUTTON_ADD_STEMS, SUF_BUTTON))()

        assert answered == [offered[:MAX_STEM_SOURCES]]

    def test_swapping_one_for_another_keeps_it_settling(self, window: GUIStemSelectionWindow) -> None:
        offered = candidates()
        answered: List[List[Path]] = []
        window.on_add = answered.append

        render(window, offered)
        pick(offered[0], picked=False)
        pick(offered[MAX_STEM_SOURCES], picked=True)
        dpg.get_item_callback(compose_tag(TAG_MAIN_CONVERTER_BUTTON_ADD_STEMS, SUF_BUTTON))()

        assert answered == [offered[1 : MAX_STEM_SOURCES + 1]]

    def test_a_pick_larger_than_a_mix_holds_waits(self, window: GUIStemSelectionWindow) -> None:
        offered = candidates()
        answered: List[List[Path]] = []
        window.on_add = answered.append

        render(window, offered)
        pick(offered[MAX_STEM_SOURCES], picked=True)

        assert add_enabled() is False
        dpg.get_item_callback(compose_tag(TAG_MAIN_CONVERTER_BUTTON_ADD_STEMS, SUF_BUTTON))()
        assert answered == []

    def test_a_pick_of_nothing_waits(self, window: GUIStemSelectionWindow) -> None:
        offered = candidates()
        render(window, offered)
        for candidate in offered[:MAX_STEM_SOURCES]:
            pick(candidate, picked=False)

        assert add_enabled() is False

    def test_letting_one_go_settles_again(self, window: GUIStemSelectionWindow) -> None:
        offered = candidates()
        render(window, offered)
        pick(offered[MAX_STEM_SOURCES], picked=True)
        assert add_enabled() is False

        pick(offered[0], picked=False)

        assert add_enabled() is True

    def test_the_line_reads_what_stands_picked(self, window: GUIStemSelectionWindow) -> None:
        offered = candidates()
        render(window, offered)
        opening = dpg.get_value(TAG_MAIN_CONVERTER_TEXT_STEM_SELECTION_LIMIT)

        pick(offered[MAX_STEM_SOURCES], picked=True)

        assert dpg.get_value(TAG_MAIN_CONVERTER_TEXT_STEM_SELECTION_LIMIT) != opening

    def test_a_list_a_mix_already_holds_arrives_settling(self, window: GUIStemSelectionWindow) -> None:
        offered = candidates(MAX_STEM_SOURCES)
        render(window, offered)
        assert add_enabled() is True
