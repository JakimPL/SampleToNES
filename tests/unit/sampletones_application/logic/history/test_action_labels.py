import pytest

from sampletones_application.categories.elements.sequencer import (
    SequencerHistoryActionElements,
    SequencerHistoryElements,
)
from sampletones_application.categories.hierarchy import Page, Panel, TextType
from sampletones_application.categories.manager import LanguageManager
from sampletones_application.logic.history.action import HistoryAction
from sampletones_application.paths import LANG_EN
from sampletones_application.view_model.shared.history import HistoryDetailWord


@pytest.fixture
def language_manager() -> LanguageManager:
    return LanguageManager(LANG_EN)


class TestActionLabelParity:
    def test_actions_and_elements_share_the_same_values(self) -> None:
        assert {member.value for member in HistoryAction} == {member.value for member in SequencerHistoryActionElements}

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
            SequencerHistoryActionElements(action.value),
        ]

        assert label


class TestDetailWordLabels:
    @pytest.mark.parametrize("word", list(HistoryDetailWord), ids=lambda word: word.value)
    def test_every_word_resolves_a_label(
        self,
        word: HistoryDetailWord,
        language_manager: LanguageManager,
    ) -> None:
        label = language_manager[
            Page.SEQUENCER,
            Panel.HISTORY,
            TextType.LABEL,
            SequencerHistoryElements(word.value),
        ]

        assert label
