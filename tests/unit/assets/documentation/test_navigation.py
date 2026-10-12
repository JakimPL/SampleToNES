from pathlib import PurePosixPath

from assets.documentation.navigation import Navigation, NavigationEntry, NavigationGroup


class TestNavigation:
    def test_each_section_linking_published_pages_is_a_group(self, navigation: Navigation) -> None:
        assert navigation.groups == (
            NavigationGroup(
                title="Using it",
                entries=(
                    NavigationEntry(page=PurePosixPath("guide/start.md"), title="Start here"),
                    NavigationEntry(page=PurePosixPath("guide/next.md"), title="Next steps"),
                    NavigationEntry(page=PurePosixPath("glossary.md"), title="Glossary"),
                ),
            ),
        )

    def test_a_folder_leads_to_the_first_page_listed_in_it(self, navigation: Navigation) -> None:
        assert navigation.folder_pages == {"guide": PurePosixPath("guide/start.md")}
