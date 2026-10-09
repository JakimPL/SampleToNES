import pytest

from sampletones_application.categories.abstract import AbstractElement
from sampletones_application.categories.hierarchy import Page, Panel, TextType
from sampletones_application.categories.manager import LanguageManager
from sampletones_application.logic.history.action import HistoryAction
from sampletones_application.paths import LANG_EN


@pytest.fixture
def language_manager() -> LanguageManager:
    return LanguageManager(LANG_EN)


class TestActionLabels:
    def test_an_action_is_the_element_its_label_is_looked_up_by(self) -> None:
        assert issubclass(HistoryAction, AbstractElement)

    @pytest.mark.parametrize("action", list(HistoryAction), ids=lambda action: action.value)
    def test_every_action_resolves_a_label(
        self,
        action: HistoryAction,
        language_manager: LanguageManager,
    ) -> None:
        label = language_manager[
            Page.SEQUENCER,
            Panel.HISTORY,
            TextType.LABEL,
            action,
        ]

        assert label
