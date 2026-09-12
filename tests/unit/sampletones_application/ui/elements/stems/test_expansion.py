from sampletones_application.ui.elements.stems.expansion import OpenFolders
from tests.suite.base import BaseTestSuite

FIRST = "/music/loops"
SECOND = "/music/drums"


class TestOpenFolders(BaseTestSuite):
    """A folder stands as the reader last left it, and a folder that has left the list is
    forgotten with it."""

    def test_a_folder_arrives_closed(self) -> None:
        assert not OpenFolders().stands_open(FIRST)

    def test_a_toggle_opens_it(self) -> None:
        folders = OpenFolders()
        assert folders.toggle(FIRST)
        assert folders.stands_open(FIRST)

    def test_a_second_toggle_closes_it(self) -> None:
        folders = OpenFolders()
        folders.toggle(FIRST)
        assert not folders.toggle(FIRST)
        assert not folders.stands_open(FIRST)

    def test_folders_stand_apart(self) -> None:
        folders = OpenFolders()
        folders.toggle(FIRST)
        assert folders.stands_open(FIRST)
        assert not folders.stands_open(SECOND)

    def test_the_keys_name_what_stands_open(self) -> None:
        folders = OpenFolders()
        folders.toggle(FIRST)
        folders.toggle(SECOND)
        assert folders.keys == {FIRST, SECOND}

    def test_a_memory_with_nothing_open_is_falsy(self) -> None:
        folders = OpenFolders()
        assert not folders
        folders.toggle(FIRST)
        assert folders

    def test_a_folder_that_left_the_list_is_forgotten(self) -> None:
        folders = OpenFolders()
        folders.toggle(FIRST)
        folders.toggle(SECOND)
        folders.hold_to({SECOND})
        assert not folders.stands_open(FIRST)
        assert folders.stands_open(SECOND)
