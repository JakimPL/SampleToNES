from datetime import datetime
from typing import Final, List, Tuple

import dearpygui.dearpygui as dpg
import pytest

from sampletones_application.categories.manager import LanguageManager
from sampletones_application.layout.config import LayoutConfig
from sampletones_application.paths import LANG_EN
from sampletones_application.tags.settings import (
    TAG_SETTINGS_PROPERTIES_BUTTON_CANCEL,
    TAG_SETTINGS_PROPERTIES_BUTTON_OK,
    TAG_SETTINGS_PROPERTIES_INPUT_AUTHOR,
    TAG_SETTINGS_PROPERTIES_INPUT_COMMENT,
    TAG_SETTINGS_PROPERTIES_INPUT_FIRST_HIGHLIGHT,
    TAG_SETTINGS_PROPERTIES_INPUT_SECOND_HIGHLIGHT,
    TAG_SETTINGS_PROPERTIES_INPUT_TITLE,
)
from sampletones_application.ui.panels.dialogs.project_properties import (
    GUIProjectPropertiesWindow,
)
from sampletones_application.utils.gui.keyboard import KeyRouter
from sampletones_application.view_model.shared.project_properties import (
    ProjectPropertiesViewModel,
)
from sampletones_shared.constants.project import MAX_HIGHLIGHT, MIN_HIGHLIGHT
from tests.suite.shortcuts import shipped_source

LANGUAGE_MANAGER: Final[LanguageManager] = LanguageManager(LANG_EN)

TIMESTAMP: Final[datetime] = datetime(2026, 8, 10, 12, 30)
FIRST_HIGHLIGHT: Final[int] = 4
SECOND_HIGHLIGHT: Final[int] = 12

Committed = Tuple[str, str, str, int, int]


def view_model(
    *,
    first_highlight: int = FIRST_HIGHLIGHT,
    second_highlight: int = SECOND_HIGHLIGHT,
) -> ProjectPropertiesViewModel:
    return ProjectPropertiesViewModel(
        title="Chiptune",
        author="Composer",
        comment="A note to self",
        first_highlight=first_highlight,
        second_highlight=second_highlight,
        created=TIMESTAMP,
        modified=TIMESTAMP,
    )


@pytest.fixture(name="window")
def window_fixture(dpg_context: None, layout_config: LayoutConfig) -> GUIProjectPropertiesWindow:
    return GUIProjectPropertiesWindow(
        layout=layout_config.project_properties,
        language_manager=LANGUAGE_MANAGER,
        key_router=KeyRouter(),
        shortcut_source=shipped_source(),
    )


def render(
    window: GUIProjectPropertiesWindow,
    *,
    first_highlight: int = FIRST_HIGHLIGHT,
    second_highlight: int = SECOND_HIGHLIGHT,
) -> None:
    """Builds the widget tree for the given project, the way ``open`` does without a live frame."""
    window._seed(
        view_model(
            first_highlight=first_highlight,
            second_highlight=second_highlight,
        )
    )
    window.create_window()


class TestProjectPropertiesWindow:
    def test_the_info_shows_the_project_s_own(self, window: GUIProjectPropertiesWindow) -> None:
        render(window)

        assert dpg.get_value(TAG_SETTINGS_PROPERTIES_INPUT_TITLE) == "Chiptune"
        assert dpg.get_value(TAG_SETTINGS_PROPERTIES_INPUT_AUTHOR) == "Composer"
        assert dpg.get_value(TAG_SETTINGS_PROPERTIES_INPUT_COMMENT) == "A note to self"

    def test_the_metre_shows_the_project_s_highlights(self, window: GUIProjectPropertiesWindow) -> None:
        render(window)

        assert dpg.get_value(TAG_SETTINGS_PROPERTIES_INPUT_FIRST_HIGHLIGHT) == FIRST_HIGHLIGHT
        assert dpg.get_value(TAG_SETTINGS_PROPERTIES_INPUT_SECOND_HIGHLIGHT) == SECOND_HIGHLIGHT

    def test_each_highlight_field_holds_the_range_the_project_accepts(
        self,
        window: GUIProjectPropertiesWindow,
    ) -> None:
        render(window)

        for tag in (
            TAG_SETTINGS_PROPERTIES_INPUT_FIRST_HIGHLIGHT,
            TAG_SETTINGS_PROPERTIES_INPUT_SECOND_HIGHLIGHT,
        ):
            configuration = dpg.get_item_configuration(tag)
            assert configuration["min_value"] == MIN_HIGHLIGHT
            assert configuration["max_value"] == MAX_HIGHLIGHT

    def test_both_actions_are_offered(self, window: GUIProjectPropertiesWindow) -> None:
        render(window)

        assert dpg.does_item_exist(TAG_SETTINGS_PROPERTIES_BUTTON_OK)
        assert dpg.does_item_exist(TAG_SETTINGS_PROPERTIES_BUTTON_CANCEL)


class TestCommit:
    """Confirming reports the whole form at once, so the owner applies one undoable gesture."""

    @pytest.fixture(name="committed")
    def committed_fixture(self, window: GUIProjectPropertiesWindow) -> List[Committed]:
        committed: List[Committed] = []
        window.on_commit = lambda title, author, comment, first_highlight, second_highlight: committed.append(
            (title, author, comment, first_highlight, second_highlight)
        )
        render(window)
        return committed

    def test_the_edited_metre_reaches_the_owner(
        self,
        window: GUIProjectPropertiesWindow,
        committed: List[Committed],
    ) -> None:
        dpg.set_value(TAG_SETTINGS_PROPERTIES_INPUT_FIRST_HIGHLIGHT, 3)
        dpg.set_value(TAG_SETTINGS_PROPERTIES_INPUT_SECOND_HIGHLIGHT, 9)

        window._commit()

        assert committed == [("Chiptune", "Composer", "A note to self", 3, 9)]

    def test_a_highlight_past_the_range_arrives_clamped(
        self,
        window: GUIProjectPropertiesWindow,
        committed: List[Committed],
    ) -> None:
        """The project rejects a highlight outside its bounds, so the dialog reports one inside."""
        dpg.set_value(TAG_SETTINGS_PROPERTIES_INPUT_FIRST_HIGHLIGHT, MAX_HIGHLIGHT + 1)
        dpg.set_value(TAG_SETTINGS_PROPERTIES_INPUT_SECOND_HIGHLIGHT, MIN_HIGHLIGHT - 1)

        window._commit()

        assert committed[-1][3:] == (MAX_HIGHLIGHT, MIN_HIGHLIGHT)

    def test_the_metre_carries_the_info_with_it(
        self,
        window: GUIProjectPropertiesWindow,
        committed: List[Committed],
    ) -> None:
        dpg.set_value(TAG_SETTINGS_PROPERTIES_INPUT_TITLE, "Another song")

        window._commit()

        assert committed[-1] == (
            "Another song",
            "Composer",
            "A note to self",
            FIRST_HIGHLIGHT,
            SECOND_HIGHLIGHT,
        )
