import operator
from pathlib import Path
from typing import Final

import pytest

from automation.dearpygui.items.types import Item
from automation.screen import Screen
from automation.vocabulary.libraries import LIBRARY_LOADED
from automation.worlds.home import World
from sampletones_application.categories.hierarchy import Tab
from sampletones_core.compatibility.kind import ObjectKind
from sampletones_core.configs import Config, InstructionsLibraryConfig
from sampletones_core.fft import Window
from sampletones_core.library.key import InstructionLibraryKey
from sampletones_shared.application import SAMPLETONES_LIBRARY_DATA_VERSION
from sampletones_shared.paths.user import LIBRARY_DIRECTORY
from tests.screens.application.old_files.steps import world_of
from tests.suite.compatibility import ARCHIVED_VERSIONS, archived, stored_document, stored_version
from tests.suite.screens.seeds.archives import archived_document

CONFIG_FIELD: Final[str] = "config"
OUTDATED_ROW: Final[str] = "instructions.library.template.library_node_outdated_template"
REBUILD_TIMEOUT_SECONDS: Final[float] = 300.0


def archived_library_path() -> Path:
    """Where the archived library lies in the library folder, named as its settings name a library file."""
    document = stored_document(archived(ObjectKind.LIBRARY, ARCHIVED_VERSIONS[ObjectKind.LIBRARY]))
    config = Config(library=InstructionsLibraryConfig.model_validate(document[CONFIG_FIELD]))
    key = InstructionLibraryKey.create(config.library, Window.from_config(config))
    return LIBRARY_DIRECTORY / key.filename


class TestTheLastReleasesLibrary:
    """A library the last release built reads as out of date, and only a rebuild the user asks for replaces
    it.

    The Instructions tab marks the library as outdated. Opening it asks about a rebuild; Cancel keeps the
    file as it was, and the next opening asks again. Confirming rebuilds the library in place: the row
    loses its mark, the file holds the current data version, and the folder holds that file alone.
    """

    @pytest.fixture
    def world(self) -> World:
        """The home holds the last release's library file."""
        return world_of(archived_document(ObjectKind.LIBRARY, archived_library_path()))

    def test_cancel_leaves_it_and_rebuild_rebuilds_it_in_place(self, screen: Screen) -> None:
        """Cancel keeps the file's bytes; the rebuild replaces the file in place."""
        library = screen.instructions.library
        path = archived_library_path()
        archived_bytes = path.read_bytes()
        outdated_mark = screen.words(OUTDATED_ROW).format("")

        def library_row() -> Item:
            return screen.expect_item(lambda: library.row(path.name), description="the library's row")

        def reads_out_of_date(screen: Screen) -> None:
            screen.tabs.bring_to_front(Tab.INSTRUCTIONS)

            assert library.tree.label(library_row()).startswith(outdated_mark)

        def cancel_leaves_it(screen: Screen) -> None:
            prompt = library.rebuild_prompt
            library.tree.open_by_click(library_row())
            screen.expect(prompt.is_shown, bool, description="the rebuild question")

            prompt.cancel()

            screen.expect(prompt.is_shown, operator.not_, description="the question gone")
            row = library_row()
            if library.tree.is_open(row):
                library.tree.open_by_click(row)
                screen.expect(lambda: library.tree.is_open(row), operator.not_, description="the row closed")
            library.tree.open_by_click(row)
            screen.expect(prompt.is_shown, bool, description="the rebuild question asked at the next opening")
            assert path.read_bytes() == archived_bytes

        def rebuild_replaces_it_in_place(screen: Screen) -> None:
            name = library.tree.label(library_row()).removeprefix(outdated_mark)

            library.rebuild_prompt.confirm()

            screen.bridge.expect(
                library.status,
                screen.words(LIBRARY_LOADED).format(name).__eq__,
                description="the rebuilt library loaded",
                timeout=REBUILD_TIMEOUT_SECONDS,
            )
            assert library.tree.label(library_row()) == name
            assert stored_version(ObjectKind.LIBRARY, path) == SAMPLETONES_LIBRARY_DATA_VERSION
            assert sorted(LIBRARY_DIRECTORY.glob(f"*{path.suffix}")) == [path]

        screen.scenario(reads_out_of_date, cancel_leaves_it, rebuild_replaces_it_in_place).run()
