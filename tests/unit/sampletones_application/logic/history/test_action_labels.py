import pytest

from sampletones_application.categories.elements.sequencer import SequencerHistoryActionElements
from sampletones_application.categories.hierarchy import Page, Panel, TextType
from sampletones_application.categories.manager import LanguageManager
from sampletones_application.logic.history.action import HistoryAction
from sampletones_application.paths import LANG_EN


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
