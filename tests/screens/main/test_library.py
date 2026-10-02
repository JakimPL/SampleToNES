import operator
from functools import partial
from pathlib import Path
from typing import Final, List

import dearpygui.dearpygui as dpg
import pytest

from sampletones_application.categories.hierarchy import Tab
from sampletones_core.configs import Config
from sampletones_core.constants.enums import SpectrumMethod
from sampletones_core.fft import Window
from sampletones_core.library.key import InstructionLibraryKey
from sampletones_core.structures.tree.node import GeneratorNode
from sampletones_shared.paths.user import LIBRARY_DIRECTORY
from tests.suite.screens.boundaries.dialogs import DialogKind
from tests.suite.screens.dearpygui.items import Item, find_item
from tests.suite.screens.screen import Screen
from tests.suite.screens.seeds import MiniLibrary, archived_library
from tests.suite.screens.steps.main import home_path
from tests.suite.screens.world import World, one_worker_config, screen_filling_state

QUICK_SAMPLE_RATE: Final[int] = 11025
GENERATION_TIMEOUT_SECONDS: Final[float] = 300.0
OTHER_LIBRARIES: Final[str] = "Other libraries"

LIBRARY_LOADED: Final[str] = "instructions.library.template.library_loaded_template"
LIBRARY_MISSING: Final[str] = "instructions.library.template.library_not_exists_template"
GENERATE: Final[str] = "instructions.library.label.generate_library_button"
REGENERATE: Final[str] = "instructions.library.label.regenerate_library_button"
GENERATION_CANCELED: Final[str] = "instructions.library.message.status_generation_canceled"


def quick_config() -> Config:
    """Settings whose library generates in seconds: a low sample rate, measured by the plain spectrum."""
    config = one_worker_config()
    library = config.library.model_copy(
        update={"sample_rate": QUICK_SAMPLE_RATE, "spectrum_method": SpectrumMethod.FFT}
    )
    return config.model_copy(update={"library": library})


def library_path(config: Config) -> Path:
    key = InstructionLibraryKey.create(config.library, Window.from_config(config))
    return LIBRARY_DIRECTORY / key.filename


def library_world(config: Config, *, built: bool) -> World:
    state = screen_filling_state().model_copy(update={"advanced_settings": True})
    return World(
        state=state,
        application_config=None,
        config=config,
        files=(MiniLibrary(config),) if built else (),
    )


def library_row(screen: Screen, path: Path) -> Item:
    library = screen.instructions.library
    return screen.expect_item(partial(library.row, path.name), description=f"the row of {path.name}")


def open_library_row(screen: Screen, row: Item) -> None:
    """Opens a library's row, which is the click that loads it, closing it first where it stands open."""
    tree = screen.instructions.library.tree
    if tree.is_open(row):
        tree.open_by_click(row)
        screen.expect(partial(tree.is_open, row), operator.not_, description="the row closed")

    tree.open_by_click(row)


def generator_rows(screen: Screen, row: Item) -> List[Item]:
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


class TestGeneratingALibrary:
    """A configuration with no library generates one, which the tree lists and the status reads as loaded."""

    @pytest.fixture
    def world(self) -> World:
        return library_world(quick_config(), built=False)

    def test_generate_lists_it_loaded_and_offers_regenerate(self, screen: Screen) -> None:
        library = screen.instructions.library
        path = library_path(quick_config())

        def nothing_to_list(screen: Screen) -> None:
            screen.tabs.bring_to_front(Tab.INSTRUCTIONS)

            screen.expect(library.generate_label, screen.words(GENERATE).__eq__, description="Generate offered")
            assert library.row(path.name) is None

        def generate(screen: Screen) -> None:
            library.generate()

            row = screen.bridge.expect(
                partial(library.row, path.name),
                lambda found: found is not None,
                description="the library listed",
                timeout=GENERATION_TIMEOUT_SECONDS,
            )
            assert row is not None
            name = library.tree.label(row)
            screen.bridge.expect(
                library.status,
                screen.words(LIBRARY_LOADED).format(name).__eq__,
                description="the library loaded",
                timeout=GENERATION_TIMEOUT_SECONDS,
            )
            assert library.generate_label() == screen.words(REGENERATE)
            assert path.exists()

        screen.scenario(nothing_to_list, generate).run()

    def test_cancelling_a_generation_leaves_no_library(self, screen: Screen) -> None:
        library = screen.instructions.library
        path = library_path(quick_config())

        def start_and_cancel(screen: Screen) -> None:
            screen.tabs.bring_to_front(Tab.INSTRUCTIONS)
            library.generate()

            library.cancel_generation()

            screen.bridge.expect(
                library.notice.is_shown, bool, description="the cancel reported", timeout=GENERATION_TIMEOUT_SECONDS
            )
            assert library.notice.words() == screen.words(GENERATION_CANCELED)
            library.notice.dismiss()
            screen.expect(library.notice.is_shown, operator.not_, description="the report dismissed")

        def nothing_was_written(screen: Screen) -> None:
            screen.expect(library.generate_label, screen.words(GENERATE).__eq__, description="Generate offered again")

            assert not path.exists()
            assert library.row(path.name) is None
            assert library.status().endswith(screen.words(LIBRARY_MISSING).format(""))

        screen.scenario(start_and_cancel, nothing_was_written).run()


class TestRegeneratingALibrary:
    """Regenerate asks first, and Cancel keeps the library as it stands."""

    @pytest.fixture
    def world(self) -> World:
        return library_world(one_worker_config(), built=True)

    def test_cancel_keeps_it_and_the_next_press_asks_again(self, screen: Screen) -> None:
        library = screen.instructions.library
        prompt = library.regenerate_prompt
        path = library_path(one_worker_config())
        kept: List[bytes] = []

        def regenerate_asks(screen: Screen) -> None:
            screen.tabs.bring_to_front(Tab.INSTRUCTIONS)
            library_row(screen, path)
            kept.append(path.read_bytes())

            library.generate()

            screen.expect(prompt.is_shown, bool, description="the question")

        def cancel_keeps_it(screen: Screen) -> None:
            prompt.cancel()
            screen.expect(prompt.is_shown, operator.not_, description="the question gone")

            library.generate()

            screen.expect(prompt.is_shown, bool, description="the question asked again")
            prompt.cancel()
            screen.expect(prompt.is_shown, operator.not_, description="the question gone again")
            assert path.read_bytes() == kept[0]

        screen.scenario(regenerate_asks, cancel_keeps_it).run()


class TestAnotherLibraryFolder:
    """Advanced settings pointed at another folder lists its libraries; pointed back, the first library returns loaded."""

    @pytest.fixture
    def world(self) -> World:
        config = one_worker_config()
        world = library_world(config, built=True)
        return World(
            state=world.state,
            application_config=None,
            config=config,
            files=(*world.files, archived_library(home_path(OTHER_LIBRARIES))),
        )

    def test_each_folder_lists_its_own(self, screen: Screen) -> None:
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
    """A library this build reads opens onto its generators; one another version built opens onto none."""

    @pytest.fixture
    def world(self) -> World:
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
