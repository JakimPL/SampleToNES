import operator
from typing import Dict, Final, List, Tuple

import dearpygui.dearpygui as dpg
import pytest

from sampletones_application.categories.hierarchy import Tab
from sampletones_application.tags.compose import TAG_SEPARATOR
from sampletones_application.tags.general import SUF_COLLAPSE_STRIP
from sampletones_application.tags.sequencer import TAG_SEQUENCER_HISTORY_PANEL
from tests.suite.screens.application import Startup
from tests.suite.screens.dearpygui.geometry import Rect
from tests.suite.screens.dearpygui.items import read_item
from tests.suite.screens.screen import Screen
from tests.suite.screens.steps.reconstructions import expect_open
from tests.suite.screens.views.main import Card
from tests.suite.screens.world import ARRANGED_PROJECT, PLAYABLE_RECONSTRUCTION

FILL_CARDS: Final[Tuple[str, ...]] = (TAG_SEQUENCER_HISTORY_PANEL,)
TABS: Final[Tuple[Tab, ...]] = (Tab.MAIN, Tab.RECONSTRUCTIONS, Tab.SEQUENCER, Tab.INSTRUCTIONS)
SETTLING_FRAMES: Final[int] = 8
STRIP_ENDING: Final[str] = f"{TAG_SEPARATOR}{SUF_COLLAPSE_STRIP}"


def cards_on(tab: Tab) -> List[str]:
    """The tags of the cards shown on ``tab`` that fold. Runs on the render thread."""
    cards: List[str] = []
    for item in dpg.get_all_items():
        alias = str(dpg.get_item_alias(item))
        if alias.startswith(f"{tab}{TAG_SEPARATOR}") and alias.endswith(STRIP_ENDING):
            card = alias[: -len(STRIP_ENDING)]
            if read_item(card).shown:
                cards.append(card)

    return sorted(cards)


def box(screen: Screen, item: str) -> Rect:
    rect = screen.bridge.ask(lambda: read_item(item).rect)
    assert rect is not None, f"{item} stands nowhere"
    return rect


@pytest.fixture
def startup() -> Startup:
    return Startup(reconstruction=PLAYABLE_RECONSTRUCTION, project=ARRANGED_PROJECT)


class TestEveryCardFoldsOntoItsBar:
    """Every card folds onto its bar: a card folding down keeps the bar and the card's padding around it, at its top
    edge or, for a card filling its column, at its bottom; a card folding sideways keeps its rail; unfolded, each
    stands as it stood.
    """

    def test_each_card_on_each_tab(self, screen: Screen) -> None:
        folded: Dict[str, List[str]] = {}

        def folding_down(card: Card) -> None:
            before = box(screen, card.tag)
            card.toggle()
            screen.expect(card.is_collapsed, bool, description=f"{card.tag} folded")
            screen.frames(SETTLING_FRAMES)

            collapsed = box(screen, card.tag)
            strip = box(screen, card.strip)
            padding = strip.y - collapsed.y
            assert collapsed.height == strip.height + 2 * padding, f"{card.tag}: {collapsed} around {strip}"
            if card.tag in FILL_CARDS:
                assert collapsed.y + collapsed.height == before.y + before.height, f"{card.tag} left its bottom"
            else:
                assert collapsed.y == before.y, f"{card.tag} left its top"

            card.toggle()
            screen.expect(card.is_collapsed, operator.not_, description=f"{card.tag} unfolded")
            screen.frames(SETTLING_FRAMES)
            assert box(screen, card.tag) == before, f"{card.tag} came back elsewhere"

        def folding_sideways(card: Card) -> None:
            before = box(screen, card.tag)
            card.toggle()
            screen.expect(card.is_collapsed, bool, description=f"{card.tag} folded")
            screen.frames(SETTLING_FRAMES)

            collapsed = box(screen, card.tag)
            rail = box(screen, card.rail)
            assert collapsed.height == before.height, f"{card.tag} changed its height folding sideways"
            assert collapsed.x <= rail.x and rail.x + rail.width <= collapsed.x + collapsed.width, f"{card.tag}"
            assert collapsed.width < before.width

            card.unfold_from_the_rail()
            screen.expect(card.is_collapsed, operator.not_, description=f"{card.tag} unfolded")
            screen.frames(SETTLING_FRAMES)
            assert box(screen, card.tag) == before, f"{card.tag} came back elsewhere"

        def fold_every_card(screen: Screen) -> None:
            expect_open(screen, PLAYABLE_RECONSTRUCTION)
            for tab in TABS:
                screen.tabs.bring_to_front(tab)
                screen.frames(SETTLING_FRAMES)
                folded[tab] = screen.bridge.ask(lambda: cards_on(tab))
                assert folded[tab], f"no card folds on {tab}"
                for tag in folded[tab]:
                    card = screen.main.card(tag)
                    if card.folds_sideways():
                        folding_sideways(card)
                    else:
                        folding_down(card)

        screen.scenario(fold_every_card).run()
