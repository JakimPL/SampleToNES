import pytest

from automation.screen import Screen
from automation.worlds.home import World, screen_filling_state
from automation.written import written_state
from sampletones_application.tags.main import TAG_MAIN_CONVERTER_PANEL
from sampletones_application.utils.gui.shortcuts.ids import ShortcutId
from tests.screens.application.restart.steps import leave, state_with_advanced, world_with


class TestTheAdvancedCardAcrossARestart:
    """Whether Advanced settings stands is written as the application leaves, and read as it starts."""

    @pytest.fixture(params=[False, True], ids=["hidden", "shown"])
    def seeded(self, request: pytest.FixtureRequest) -> bool:
        """The state the session holds: hidden or shown."""
        shown: bool = request.param
        return shown

    @pytest.fixture
    def world(self, seeded: bool) -> World:
        """The home holds a session with Advanced settings as seeded."""
        return world_with(state_with_advanced(seeded))

    def test_a_home_holding_it_shows_it(self, screen: Screen, seeded: bool) -> None:
        """The card is shown as the session says."""
        screen.expect(screen.main.advanced.is_shown, seeded.__eq__, description="the card as the session says")

    def test_leaving_writes_the_toggled_state(self, screen: Screen, seeded: bool) -> None:
        """After the toggle shortcut and Exit, the session holds the opposite of the seeded state."""
        screen.press_shortcut(ShortcutId.TOGGLE_ADVANCED_SETTINGS)
        screen.expect(screen.main.advanced.is_shown, seeded.__ne__, description="the card toggled")

        leave(screen)

        assert written_state().advanced_settings is not seeded


class TestACollapsedCardAcrossARestart:
    """A card folded into its bar is written as the application leaves, and stands folded at next start."""

    @pytest.fixture(params=[False, True], ids=["open", "collapsed"])
    def seeded(self, request: pytest.FixtureRequest) -> bool:
        """The state the session holds for the Converter card: open or collapsed."""
        collapsed: bool = request.param
        return collapsed

    @pytest.fixture
    def world(self, seeded: bool) -> World:
        """The home holds a session with the Converter card as seeded."""
        state = screen_filling_state().model_copy(update={"collapsed_cards": {TAG_MAIN_CONVERTER_PANEL: seeded}})
        return world_with(state)

    def test_a_home_holding_it_shows_it(self, screen: Screen, seeded: bool) -> None:
        """The Converter card is collapsed as the session says."""
        card = screen.main.card(TAG_MAIN_CONVERTER_PANEL)

        screen.expect(card.is_collapsed, seeded.__eq__, description="the Converter card as the session says")

    def test_leaving_writes_the_toggled_state(self, screen: Screen, seeded: bool) -> None:
        """After the toggle and Exit, the session holds the opposite of the seeded state."""
        card = screen.main.card(TAG_MAIN_CONVERTER_PANEL)
        screen.expect(card.is_collapsed, seeded.__eq__, description="the Converter card as the session says")

        card.toggle()

        screen.expect(card.is_collapsed, seeded.__ne__, description="the Converter card toggled")
        leave(screen)
        assert written_state().collapsed_cards.get(TAG_MAIN_CONVERTER_PANEL) is not seeded
