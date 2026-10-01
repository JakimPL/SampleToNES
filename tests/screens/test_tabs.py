from sampletones_application.categories.hierarchy import Tab
from tests.suite.screens.screen import Screen


class TestTabs:
    """The tab bar across the window brings a tab forward at a click on its header."""

    def test_each_header_brings_its_tab_forward(self, screen: Screen) -> None:
        for tab in (Tab.RECONSTRUCTIONS, Tab.SEQUENCER, Tab.INSTRUCTIONS, Tab.MAIN):
            screen.tabs.bring_to_front(tab)

            front = screen.expect(
                screen.tabs.front,
                tab.__eq__,
                description=f"the {tab} tab in front",
            )

            assert front == tab
