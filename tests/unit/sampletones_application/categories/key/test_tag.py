from sampletones_application.categories.hierarchy import Page, Panel, Widget
from sampletones_application.categories.key.tag import TagName


class TestTagNameComposition:
    def test_full_key_names_every_segment(self) -> None:
        tag = TagName(Page.GLOBAL, Panel.GRAPH, Widget.THEME, "indicator")
        assert tag == "global.graph.theme.indicator"

    def test_implicit_panel_is_elided(self) -> None:
        tag = TagName(Page.GLOBAL, Panel.IMPLICIT, Widget.WINDOW, "main")
        assert tag == "global.window.main"

    def test_empty_element_is_elided(self) -> None:
        tag = TagName(Page.GLOBAL, Panel.IMPLICIT, Widget.TABS, "")
        assert tag == "global.tabs"

    def test_element_repeating_the_panel_is_elided(self) -> None:
        tag = TagName(Page.MAIN, Panel.CONFIG, Widget.PANEL, "config")
        assert tag == "main.config.panel"

    def test_structured_parts_stay_reachable(self) -> None:
        tag = TagName(Page.SETTINGS, Panel.AUDIO, Widget.WINDOW, "audio")
        assert (tag.page, tag.panel, tag.widget, tag.element) == (
            Page.SETTINGS,
            Panel.AUDIO,
            Widget.WINDOW,
            "audio",
        )
