from typing import Final, List

import dearpygui.dearpygui as dpg
import pytest

from sampletones_application.categories.manager import LanguageManager
from sampletones_application.layout.config import LayoutConfig
from sampletones_application.paths import LANG_EN
from sampletones_application.tags.compose import compose_tag
from sampletones_application.tags.general import SUF_BUTTON
from sampletones_application.tags.settings import (
    TAG_SETTINGS_DISPLAY_BUTTON_KEEP,
    TAG_SETTINGS_DISPLAY_BUTTON_REVERT,
    TAG_SETTINGS_DISPLAY_TEXT_COUNTDOWN,
)
from sampletones_application.ui.panels.dialogs.countdown import GUICountdownWindow
from sampletones_application.utils.gui.keyboard import KeyRouter
from tests.suite.shortcuts import shipped_source

LANGUAGE_MANAGER: Final[LanguageManager] = LanguageManager(LANG_EN)
REMAINING_FORMAT: Final[str] = LANGUAGE_MANAGER["settings.display.template.countdown_remaining"]


@pytest.fixture(name="window")
def window_fixture(dpg_context: None, layout_config: LayoutConfig) -> GUICountdownWindow:
    return GUICountdownWindow(
        layout=layout_config.settings.display.countdown,
        title=LANGUAGE_MANAGER["settings.display.title.countdown"],
        message=LANGUAGE_MANAGER["settings.display.message.countdown"],
        remaining_format=REMAINING_FORMAT,
        keep_label=LANGUAGE_MANAGER["settings.display.label.keep_button"],
        revert_label=LANGUAGE_MANAGER["settings.display.label.revert_button"],
        key_router=KeyRouter(),
        shortcut_source=shipped_source(),
    )


def render(window: GUICountdownWindow, remaining: int) -> None:
    """Builds the widget tree for the given count, the way ``open`` does without a live frame."""
    window.set_remaining(remaining)
    window.create_window()


def press(tag: str) -> None:
    dpg.get_item_callback(compose_tag(tag, SUF_BUTTON))()


class TestCountdownWindow:
    def test_the_seconds_left_are_on_the_prompt(self, window: GUICountdownWindow) -> None:
        render(window, 10)

        assert dpg.get_value(TAG_SETTINGS_DISPLAY_TEXT_COUNTDOWN) == REMAINING_FORMAT.format(seconds=10)

    def test_a_new_second_reaches_the_prompt(self, window: GUICountdownWindow) -> None:
        render(window, 10)

        window.set_remaining(9)

        assert dpg.get_value(TAG_SETTINGS_DISPLAY_TEXT_COUNTDOWN) == REMAINING_FORMAT.format(seconds=9)

    def test_both_answers_are_offered(self, window: GUICountdownWindow) -> None:
        render(window, 10)

        assert dpg.does_item_exist(TAG_SETTINGS_DISPLAY_BUTTON_KEEP)
        assert dpg.does_item_exist(TAG_SETTINGS_DISPLAY_BUTTON_REVERT)


class TestReportedAnswers:
    @pytest.fixture(name="answers")
    def answers_fixture(self, window: GUICountdownWindow) -> List[str]:
        answers: List[str] = []
        window.on_keep = lambda: answers.append("keep")
        window.on_revert = lambda: answers.append("revert")
        render(window, 10)
        return answers

    def test_keeping_reports_it(self, window: GUICountdownWindow, answers: List[str]) -> None:
        press(TAG_SETTINGS_DISPLAY_BUTTON_KEEP)

        assert answers == ["keep"]

    def test_reverting_reports_it(self, window: GUICountdownWindow, answers: List[str]) -> None:
        press(TAG_SETTINGS_DISPLAY_BUTTON_REVERT)

        assert answers == ["revert"]
