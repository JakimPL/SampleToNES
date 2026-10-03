import operator
from typing import Final, List

import dearpygui.dearpygui as dpg
import pytest

from sampletones_application.categories.hierarchy import Tab
from sampletones_core.structures.tree.node import GeneratorNode
from sampletones_shared.paths.user import LIBRARY_DIRECTORY
from tests.screens.main.library.steps import library_world
from tests.suite.screens.boundaries.dialogs import DialogKind
from tests.suite.screens.dearpygui.items.reading import find_item
from tests.suite.screens.dearpygui.items.types import Item
from tests.suite.screens.screen import Screen
from tests.suite.screens.seeds.archives import archived_library
from tests.suite.screens.steps.instructions import library_path, library_row, open_library_row
from tests.suite.screens.steps.main import home_path
from tests.suite.screens.vocabulary.libraries import LIBRARY_LOADED
from tests.suite.screens.worlds.home import World, one_worker_config

OTHER_LIBRARIES: Final[str] = "Other libraries"


def generator_rows(screen: Screen, row: Item) -> List[Item]:
    """The generator rows below the library ``row``, read on the render thread."""

    def read() -> List[Item]:
        found: List[Item] = []
        find_item(row, lambda item: _collect_generator(item, found))
        return found

    return screen.bridge.ask(read)


def _collect_generator(item: Item, found: List[Item]) -> bool:
    user_data = dpg.get_item_user_data(item)
    if isinstance(user_data, tuple) and user_data and isinstance(user_data[0], GeneratorNode):
        found.append(item)

    return False


class TestAnotherLibraryFolder:
    """Advanced settings pointed at another folder list that folder's libraries; pointed back, the first
    folder's library returns loaded.

    The first library is opened and reads loaded. The library folder is pointed at a folder holding an
    older library, where the first library is gone and the older one is flagged outdated. Pointing back
    lists the first library again and clears the older one.
    """

    @pytest.fixture
    def world(self) -> World:
        """A home holding a built library and a folder of other libraries holding an older one."""
        config = one_worker_config()
        world = library_world(config, built=True)
        return World(
            state=world.state,
            application_config=None,
            config=config,
            files=(*world.files, archived_library(home_path(OTHER_LIBRARIES))),
        )

    def test_each_folder_lists_its_own(self, screen: Screen) -> None:
        """Each library folder lists its own libraries and none of the other's."""
        library = screen.instructions.library
        main = screen.main
        ours = library_path(one_worker_config())
        names: List[str] = []

        def ours_listed_and_loaded(screen: Screen) -> None:
            screen.tabs.bring_to_front(Tab.INSTRUCTIONS)
            row = library_row(screen, ours)
            names.append(library.tree.label(row))

            open_library_row(screen, row)

            screen.expect(library.status, screen.words(LIBRARY_LOADED).format(names[0]).__eq__, description="loaded")

        def point_at_the_other_folder(screen: Screen) -> None:
            screen.tabs.bring_to_front(Tab.MAIN)
            screen.answer_next_dialog(DialogKind.DIRECTORY, home_path(OTHER_LIBRARIES))
            main.choose_library_directory()
            screen.expect(
                main.library_directory, str(home_path(OTHER_LIBRARIES)).__eq__, description="the other folder"
            )

            screen.tabs.bring_to_front(Tab.INSTRUCTIONS)

            screen.expect(lambda: library.row(ours.name) is None, bool, description="ours no longer listed")
            assert library.tree.library_row(lambda node: node.outdated) is not None

        def point_back(screen: Screen) -> None:
            screen.tabs.bring_to_front(Tab.MAIN)
            screen.answer_next_dialog(DialogKind.DIRECTORY, LIBRARY_DIRECTORY)
            main.choose_library_directory()
            screen.expect(main.library_directory, str(LIBRARY_DIRECTORY).__eq__, description="our folder")

            screen.tabs.bring_to_front(Tab.INSTRUCTIONS)

            library_row(screen, ours)
            assert library.tree.library_row(lambda node: node.outdated) is None

        screen.scenario(ours_listed_and_loaded, point_at_the_other_folder, point_back).run()

    @pytest.mark.xfail(
        strict=True,
        raises=AssertionError,
        reason="bugs-and-todos § Bugs: a library folder pointed away from and back lists its library unloaded",
    )
    def test_pointing_back_finds_the_library_loaded(self, screen: Screen) -> None:
        """After pointing away and back, the first library's status reads loaded without a second opening."""
        library = screen.instructions.library
        main = screen.main
        ours = library_path(one_worker_config())
        screen.tabs.bring_to_front(Tab.INSTRUCTIONS)
        name = library.tree.label(library_row(screen, ours))
        open_library_row(screen, library_row(screen, ours))
        screen.expect(library.status, screen.words(LIBRARY_LOADED).format(name).__eq__, description="loaded")
        screen.tabs.bring_to_front(Tab.MAIN)
        for folder in (home_path(OTHER_LIBRARIES), LIBRARY_DIRECTORY):
            screen.answer_next_dialog(DialogKind.DIRECTORY, folder)
            main.choose_library_directory()
            screen.expect(main.library_directory, str(folder).__eq__, description=f"the folder {folder.name}")

        screen.tabs.bring_to_front(Tab.INSTRUCTIONS)

        library_row(screen, ours)
        screen.expect(library.status, screen.words(LIBRARY_LOADED).format(name).__eq__, description="loaded again")


class TestGeneratorsUnderALibrary:
    """A library this build reads opens onto its generators; one another version built opens onto none.

    The old library's row asks to rebuild when opened, and Cancel keeps it closed. The current
    library's row opens onto generator rows while the old one still lists none.
    """

    @pytest.fixture
    def world(self) -> World:
        """A home holding a built library and an older library in the library folder."""
        config = one_worker_config()
        world = library_world(config, built=True)
        return World(
            state=world.state,
            application_config=None,
            config=config,
            files=(*world.files, archived_library(LIBRARY_DIRECTORY)),
        )

    def test_the_old_one_lists_none_and_ours_lists_them(self, screen: Screen) -> None:
        library = screen.instructions.library
        prompt = library.rebuild_prompt
        ours = library_path(one_worker_config())

        def the_old_one_opens_onto_nothing(screen: Screen) -> None:
            screen.tabs.bring_to_front(Tab.INSTRUCTIONS)
            old = screen.expect_item(
                lambda: library.tree.library_row(lambda node: node.outdated),
                description="the old library's row",
            )

            library.tree.open_by_click(old)

            screen.expect(prompt.is_shown, bool, description="the rebuild question")
            prompt.cancel()
            screen.expect(prompt.is_shown, operator.not_, description="the question gone")

        def ours_opens_onto_its_generators(screen: Screen) -> None:
            open_library_row(screen, library_row(screen, ours))

            screen.expect(
                lambda: len(generator_rows(screen, library_row(screen, ours))), bool, description="generator rows"
            )
            old = library.tree.library_row(lambda node: node.outdated)
            assert old is not None
            assert generator_rows(screen, old) == []

        screen.scenario(the_old_one_opens_onto_nothing, ours_opens_onto_its_generators).run()
